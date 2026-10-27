"""Reads public web pages politely and safely.

Rules this module follows on every page:
- Checks the site's robots.txt and skips pages it disallows.
- Waits between requests to the same site (at least MIN_DELAY_SECONDS, or longer if robots.txt asks).
- Never logs in, never bypasses paywalls or CAPTCHAs: such pages are skipped with a clear reason.
- Identifies itself honestly with a descriptive User-Agent.
- Refuses private / internal network addresses (so a hosted app can't be used to probe internal systems).
"""

import ipaddress
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, Optional
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from cra.models import Source

USER_AGENT = (
    "CompetitiveResearchAgent/0.1 "
    "(+https://github.com/womeninproduct3206-ux/competitive-research-agent)"
)
MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 10.0
TIMEOUT_SECONDS = 15
MAX_PAGE_BYTES = 3_000_000
MAX_TEXT_CHARS = 60_000
MIN_USEFUL_CHARS = 200
MAX_REDIRECTS = 5

# Plain-English explanations for HTTP status codes that mean "you may not read this".
BLOCKED_STATUS = {
    401: "the page requires a login",
    402: "the page is behind a paywall",
    403: "the website refused access to automated visitors",
    407: "the page requires a login",
    429: "the website asked us to slow down (too many requests); try again later",
    451: "the page is unavailable for legal reasons",
}


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    body: bytes
    final_url: str


HttpGet = Callable[[str], HttpResponse]


def default_http_get(url: str) -> HttpResponse:
    with requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain"},
                      timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=False) as resp:
        body = b""
        for chunk in resp.iter_content(64_000):
            body += chunk
            if len(body) > MAX_PAGE_BYTES:
                break
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return HttpResponse(resp.status_code, headers, body[:MAX_PAGE_BYTES], resp.url)


@dataclass
class FetchResult:
    url: str
    source: Optional[Source] = None
    skipped_reason: str = ""

    @property
    def ok(self) -> bool:
        return self.source is not None


def address_problem(host: str) -> str:
    """'' if every address the host name points to is on the public internet, else the reason."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return "we couldn't find this website - please check the address is spelled correctly"
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            return "the address points to a private network, not a public website"
    return ""


def extract_text(html: str) -> tuple:
    """Return (title, readable_text) from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(["head", "script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return title, text[:MAX_TEXT_CHARS]


def looks_access_controlled(html: str, text: str) -> str:
    """Spot login walls and CAPTCHAs we must not get past. Returns a reason, or ''."""
    lowered = html.lower()
    if "type=\"password\"" in lowered or "type='password'" in lowered:
        if len(text) < 1500:
            return "the page appears to require a login"
    if any(marker in lowered for marker in ("g-recaptcha", "h-captcha", "cf-challenge", "captcha-container")):
        return "the page shows a CAPTCHA / bot check"
    return ""


@dataclass
class Fetcher:
    http_get: HttpGet = default_http_get
    min_delay: float = MIN_DELAY_SECONDS
    allow_private_addresses: bool = False  # only for automated tests
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    _robots: Dict[str, Optional[robotparser.RobotFileParser]] = field(default_factory=dict)
    _robots_error: Dict[str, str] = field(default_factory=dict)
    _last_request: Dict[str, float] = field(default_factory=dict)

    def _wait_turn(self, site: str, delay: float) -> None:
        last = self._last_request.get(site)
        if last is not None:
            remaining = delay - (self.clock() - last)
            if remaining > 0:
                self.sleep(remaining)
        self._last_request[site] = self.clock()

    def _robots_for(self, site: str) -> Optional[robotparser.RobotFileParser]:
        """Load robots.txt once per site. None means we must not crawl (reason in _robots_error)."""
        if site in self._robots:
            return self._robots[site]
        parser = robotparser.RobotFileParser()
        self._wait_turn(site, self.min_delay)
        try:
            robots_url = f"{site}/robots.txt"
            resp = self.http_get(robots_url)
            for _ in range(MAX_REDIRECTS):  # robots.txt may redirect, e.g. to the www. address
                if resp.status not in (301, 302, 303, 307, 308) or not resp.headers.get("location"):
                    break
                robots_url = urljoin(robots_url, resp.headers["location"])
                resp = self.http_get(robots_url)
        except requests.RequestException:
            self._robots_error[site] = "we couldn't reach the website to check its robots.txt rules"
            self._robots[site] = None
            return None
        if resp.status in (401, 403):
            parser.disallow_all = True
        elif resp.status >= 500:
            self._robots_error[site] = "the website's robots.txt was temporarily unavailable, so we didn't crawl it"
            self._robots[site] = None
            return None
        elif resp.status >= 400 or resp.status in (301, 302, 303, 307, 308):
            parser.allow_all = True  # no robots.txt means no restrictions
        else:
            parser.parse(resp.body.decode("utf-8", errors="replace").splitlines())
        self._robots[site] = parser
        return parser

    def fetch(self, url: str) -> FetchResult:
        """Read one page. Redirects are followed one hop at a time so every hop gets the same checks."""
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            result, next_url = self._fetch_once(current)
            if next_url is None:
                result.url = url
                return result
            current = next_url
        return FetchResult(url, skipped_reason="the page redirected too many times")

    def _fetch_once(self, url: str) -> tuple:
        """Returns (FetchResult, None) when done, or (None, next_url) for a redirect."""
        result = self._fetch_page(url)
        if isinstance(result, str):
            return None, result
        return result, None

    def _fetch_page(self, url: str):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return FetchResult(url, skipped_reason="this is not a web page address")
        problem = "" if self.allow_private_addresses else address_problem(parsed.hostname)
        if problem:
            return FetchResult(url, skipped_reason=problem)
        site = f"{parsed.scheme}://{parsed.netloc}"

        robots = self._robots_for(site)
        if robots is None:
            return FetchResult(url, skipped_reason=self._robots_error[site])
        if not robots.can_fetch(USER_AGENT, url):
            return FetchResult(url, skipped_reason="the website's robots.txt asks automated tools not to read this page")

        crawl_delay = robots.crawl_delay(USER_AGENT) or 0
        self._wait_turn(site, min(max(self.min_delay, float(crawl_delay)), MAX_DELAY_SECONDS))
        try:
            resp = self.http_get(url)
        except requests.Timeout:
            return FetchResult(url, skipped_reason="the website took too long to respond")
        except requests.RequestException:
            return FetchResult(url, skipped_reason="we couldn't connect to the website")

        if resp.status in (301, 302, 303, 307, 308) and resp.headers.get("location"):
            return urljoin(url, resp.headers["location"])
        if resp.status in BLOCKED_STATUS:
            return FetchResult(url, skipped_reason=BLOCKED_STATUS[resp.status])
        if resp.status == 404:
            return FetchResult(url, skipped_reason="the page was not found (404) - please check the address")
        if resp.status >= 400:
            return FetchResult(url, skipped_reason=f"the website returned an error (code {resp.status})")

        content_type = resp.headers.get("content-type", "text/html").lower()
        if "html" not in content_type and "text/plain" not in content_type:
            return FetchResult(url, skipped_reason=f"the page isn't a web page we can read yet ({content_type.split(';')[0]})")

        html = resp.body.decode("utf-8", errors="replace")
        if "html" in content_type:
            title, text = extract_text(html)
        else:
            title, text = "", html[:MAX_TEXT_CHARS]
        blocked = looks_access_controlled(html, text)
        if blocked:
            return FetchResult(url, skipped_reason=blocked)
        if len(text) < MIN_USEFUL_CHARS:
            return FetchResult(url, skipped_reason="the page had almost no readable text "
                                                   "(it may need JavaScript to load its content)")

        source = Source(
            title=title or parsed.netloc + parsed.path,
            url=url,
            accessed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            excerpt=" ".join(text.split())[:300],
            text=text,
        )
        return FetchResult(url, source=source)
