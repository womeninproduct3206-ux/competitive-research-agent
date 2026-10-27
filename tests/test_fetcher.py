import requests

from cra.fetcher import Fetcher, HttpResponse
from cra.models import Competitor
from cra.pipeline import run_research
from tests.helpers import sample_request

ARTICLE = "<p>" + "Our Team plan costs $12 per user per month and includes priority support. " * 5 + "</p>"
PAGE = f"<html><head><title>Pricing - Acme</title></head><body><nav>Menu</nav>{ARTICLE}</body></html>"


class FakeWeb:
    """Pretend internet: maps URL -> (status, headers, body). Records every request."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        if url not in self.pages:
            return HttpResponse(404, {}, b"", url)
        page = self.pages[url]
        if isinstance(page, Exception):
            raise page
        status, headers, body = page
        return HttpResponse(status, {"content-type": "text/html", **headers}, body.encode(), url)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_fetcher(pages, min_delay=2.0):
    web, clock = FakeWeb(pages), FakeClock()
    fetcher = Fetcher(http_get=web.get, min_delay=min_delay, allow_private_addresses=True,
                      sleep=clock.sleep, clock=clock.time)
    return fetcher, web, clock


def test_reads_a_public_page_and_records_source():
    fetcher, _, _ = make_fetcher({"https://acme.test/pricing": (200, {}, PAGE)})
    result = fetcher.fetch("https://acme.test/pricing")
    assert result.ok
    assert result.source.title == "Pricing - Acme"
    assert "$12 per user per month" in result.source.text
    assert "Menu" not in result.source.text  # navigation is stripped
    assert result.source.accessed_at.endswith("Z")


def test_respects_robots_txt_disallow():
    fetcher, web, _ = make_fetcher({
        "https://acme.test/robots.txt": (200, {}, "User-agent: *\nDisallow: /private"),
        "https://acme.test/private/page": (200, {}, PAGE),
    })
    result = fetcher.fetch("https://acme.test/private/page")
    assert not result.ok and "robots.txt" in result.skipped_reason
    assert "https://acme.test/private/page" not in web.requested  # never even downloaded


def test_robots_txt_is_checked_once_per_site():
    fetcher, web, _ = make_fetcher({"https://acme.test/a": (200, {}, PAGE), "https://acme.test/b": (200, {}, PAGE)})
    fetcher.fetch("https://acme.test/a")
    fetcher.fetch("https://acme.test/b")
    assert web.requested.count("https://acme.test/robots.txt") == 1


def test_waits_between_requests_to_the_same_site():
    fetcher, _, clock = make_fetcher({"https://acme.test/a": (200, {}, PAGE), "https://acme.test/b": (200, {}, PAGE)})
    fetcher.fetch("https://acme.test/a")
    fetcher.fetch("https://acme.test/b")
    assert len(clock.sleeps) >= 2 and all(s >= 2.0 for s in clock.sleeps)


def test_honours_robots_crawl_delay():
    fetcher, _, clock = make_fetcher({
        "https://acme.test/robots.txt": (200, {}, "User-agent: *\nCrawl-delay: 5"),
        "https://acme.test/a": (200, {}, PAGE),
    })
    fetcher.fetch("https://acme.test/a")
    assert clock.sleeps == [5.0]


def test_access_controlled_pages_are_skipped():
    login = "<html><body><form><input type='password'></form>Sign in</body></html>"
    captcha = f"<html><body><div class='g-recaptcha'></div>{ARTICLE}</body></html>"
    fetcher, _, _ = make_fetcher({
        "https://acme.test/members": (401, {}, ""),
        "https://acme.test/premium": (402, {}, ""),
        "https://acme.test/blocked": (403, {}, ""),
        "https://acme.test/login": (200, {}, login),
        "https://acme.test/check": (200, {}, captcha),
    }, min_delay=0)
    reasons = {path: fetcher.fetch(f"https://acme.test/{path}").skipped_reason
               for path in ["members", "premium", "blocked", "login", "check"]}
    assert "login" in reasons["members"]
    assert "paywall" in reasons["premium"]
    assert "refused" in reasons["blocked"]
    assert "login" in reasons["login"]
    assert "CAPTCHA" in reasons["check"]


def test_unreadable_pages_get_helpful_reasons():
    fetcher, _, _ = make_fetcher({
        "https://acme.test/app": (200, {}, "<html><body><div id='root'></div></body></html>"),
        "https://acme.test/file": (200, {"content-type": "application/pdf"}, "%PDF"),
        "https://acme.test/down": requests.ConnectionError(),
    }, min_delay=0)
    assert "JavaScript" in fetcher.fetch("https://acme.test/app").skipped_reason
    assert "application/pdf" in fetcher.fetch("https://acme.test/file").skipped_reason
    assert "couldn't connect" in fetcher.fetch("https://acme.test/down").skipped_reason
    assert "404" in fetcher.fetch("https://acme.test/missing").skipped_reason


def test_redirect_to_another_site_is_rechecked_against_its_robots_txt():
    fetcher, web, _ = make_fetcher({
        "https://acme.test/go": (301, {"location": "https://other.test/page"}, ""),
        "https://other.test/robots.txt": (200, {}, "User-agent: *\nDisallow: /"),
        "https://other.test/page": (200, {}, PAGE),
    }, min_delay=0)
    result = fetcher.fetch("https://acme.test/go")
    assert not result.ok and "robots.txt" in result.skipped_reason
    assert "https://other.test/page" not in web.requested


def test_private_addresses_are_refused_by_default():
    result = Fetcher().fetch("http://127.0.0.1/admin")
    assert not result.ok and "private network" in result.skipped_reason


def test_unknown_website_gets_spelling_hint():
    result = Fetcher().fetch("https://no-such-site.invalid/")
    assert not result.ok and "spelled correctly" in result.skipped_reason


def test_live_pipeline_collects_sources_and_lists_skipped_pages():
    fetcher, _, _ = make_fetcher({
        "https://acme.test/pricing": (200, {}, PAGE),
        "https://acme.test/secret": (403, {}, ""),
    }, min_delay=0)
    request = sample_request()
    request.competitors = [Competitor("Acme", ["https://acme.test/pricing", "https://acme.test/secret"])]
    report = run_research(request, live=True, fetcher=fetcher)
    assert not report.is_demo
    assert [s.url for s in report.sources] == ["https://acme.test/pricing"]
    assert report.skipped_pages[0].url == "https://acme.test/secret"
    assert report.claims == []  # no invented findings without AI analysis
