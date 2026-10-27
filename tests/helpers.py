from cra.models import Competitor, ResearchCategory, ResearchRequest


def sample_request(categories=None):
    return ResearchRequest(
        product_name="Demo Product",
        product_description="A sample product",
        industry="Software",
        target_customer="Small teams",
        competitors=[Competitor("Demo Brand A", ["https://demo-brand-a.example.com/"])],
        objectives="Learn about pricing",
        categories=list(categories or ResearchCategory),
    )
