"""Checks the research setup form and turns it into a ResearchRequest.

Every problem is reported as a plain-English message the user can act on.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple
from urllib.parse import urlparse

from cra.models import Competitor, ResearchCategory, ResearchRequest

MAX_COMPETITORS = 5
MAX_URLS_PER_COMPETITOR = 10


@dataclass
class CompetitorInput:
    """Raw text typed into one competitor box of the form."""

    name: str = ""
    urls_text: str = ""  # one URL per line


@dataclass
class FormInput:
    product_name: str = ""
    product_description: str = ""
    industry: str = ""
    target_customer: str = ""
    competitors: List[CompetitorInput] = field(default_factory=list)
    objectives: str = ""
    categories: Sequence[ResearchCategory] = ()


def normalize_url(raw: str) -> Optional[str]:
    """Return a clean http(s) URL, adding https:// if missing. None if it isn't a web address."""
    text = raw.strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        return None
    host = parsed.hostname or ""
    if "." not in host or " " in text:
        return None
    return text


def parse_urls(urls_text: str) -> Tuple[List[str], List[str]]:
    """Split a box of URLs into (valid, invalid) lists, dropping duplicates."""
    valid: List[str] = []
    invalid: List[str] = []
    for line in urls_text.replace(",", "\n").splitlines():
        if not line.strip():
            continue
        url = normalize_url(line)
        if url is None:
            invalid.append(line.strip())
        elif url not in valid:
            valid.append(url)
    return valid, invalid


def validate_form(form: FormInput) -> Tuple[Optional[ResearchRequest], List[str]]:
    """Return (request, []) when the form is complete, or (None, error messages)."""
    errors: List[str] = []

    if not form.product_name.strip():
        errors.append("Please enter your product name.")
    if not form.product_description.strip():
        errors.append("Please add a short description of your product.")
    if not form.industry.strip():
        errors.append("Please enter your industry.")
    if not form.target_customer.strip():
        errors.append("Please describe your target customer.")
    if not form.objectives.strip():
        errors.append("Please write at least one research objective or question.")
    if not form.categories:
        errors.append("Please choose at least one research category.")

    competitors: List[Competitor] = []
    seen_names = set()
    for entry in form.competitors:
        name = entry.name.strip()
        if not name and not entry.urls_text.strip():
            continue  # an empty box - ignore it
        label = name or "A competitor"
        if not name:
            errors.append("One competitor has web addresses but no name. Please add its name.")
        elif name.lower() in seen_names:
            errors.append(f"'{name}' is listed more than once.")
        seen_names.add(name.lower())

        urls, bad = parse_urls(entry.urls_text)
        for item in bad:
            errors.append(f"{label}: '{item}' doesn't look like a web address (example: https://example.com/pricing).")
        if not urls and not bad:
            errors.append(f"{label}: please add at least one public web page to research.")
        if len(urls) > MAX_URLS_PER_COMPETITOR:
            errors.append(f"{label}: please list at most {MAX_URLS_PER_COMPETITOR} web pages.")
        competitors.append(Competitor(name=name, urls=urls))

    if not competitors:
        errors.append("Please add at least one competitor.")
    elif len(competitors) > MAX_COMPETITORS:
        errors.append(f"Please research at most {MAX_COMPETITORS} competitors at a time.")

    if errors:
        return None, errors

    request = ResearchRequest(
        product_name=form.product_name.strip(),
        product_description=form.product_description.strip(),
        industry=form.industry.strip(),
        target_customer=form.target_customer.strip(),
        competitors=competitors,
        objectives=form.objectives.strip(),
        categories=list(form.categories),
    )
    return request, []
