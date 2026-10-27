from cra.models import ResearchCategory
from cra.validation import CompetitorInput, FormInput, normalize_url, parse_urls, validate_form


def complete_form(**overrides):
    values = dict(
        product_name="Demo Product",
        product_description="A sample product",
        industry="Frozen desserts",
        target_customer="Health-conscious adults",
        competitors=[CompetitorInput("Demo Brand A", "demo-a.example.com\nhttps://demo-a.example.com/pricing")],
        objectives="How do competitors price their products?",
        categories=[ResearchCategory.PRICING],
    )
    values.update(overrides)
    return FormInput(**values)


def test_normalize_url():
    assert normalize_url("example.com/pricing") == "https://example.com/pricing"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("ftp://example.com") is None
    assert normalize_url("not a url") is None
    assert normalize_url("   ") is None


def test_parse_urls_splits_valid_invalid_and_dedupes():
    valid, invalid = parse_urls("example.com\nhttps://example.com\n\nhello world, b.example.org")
    assert valid == ["https://example.com", "https://b.example.org"]
    assert invalid == ["hello world"]


def test_complete_form_is_valid():
    request, errors = validate_form(complete_form())
    assert errors == []
    assert request.competitors[0].urls == ["https://demo-a.example.com", "https://demo-a.example.com/pricing"]


def test_empty_form_lists_every_problem():
    request, errors = validate_form(FormInput())
    assert request is None
    assert "Please enter your product name." in errors
    assert "Please add at least one competitor." in errors
    assert "Please choose at least one research category." in errors


def test_competitor_problems_are_reported():
    form = complete_form(competitors=[
        CompetitorInput("Demo Brand A", ""),
        CompetitorInput("demo brand a", "example.com"),
        CompetitorInput("", "example.org"),
        CompetitorInput("Demo Brand C", "bad url"),
    ])
    _, errors = validate_form(form)
    assert any("Demo Brand A: please add at least one" in e for e in errors)
    assert any("listed more than once" in e for e in errors)
    assert any("no name" in e for e in errors)
    assert any("'bad url' doesn't look like a web address" in e for e in errors)


def test_blank_competitor_rows_are_ignored():
    form = complete_form(competitors=[CompetitorInput(), complete_form().competitors[0], CompetitorInput()])
    request, errors = validate_form(form)
    assert errors == []
    assert len(request.competitors) == 1
