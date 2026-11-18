"""The structured shape Claude must fill in for each article."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

CATEGORIES = (
    "Wedding",
    "Family Function",
    "Décor & Design",
    "Event Tech",
    "Corporate & MICE",
    "Concerts & Festivals",
    "Culture & Celebrations",
    "Industry News",
    "Tips & Trends",
    "Viral Moment",
)
REGIONS = ("Tamil Nadu", "India", "Global", "East Asia", "Middle East")


class VerifiedIntelExtraction(BaseModel):
    is_relevant: bool = Field(
        description=(
            "True if the item is mainly about events in any form: weddings and receptions, family "
            "functions (birthdays, baby showers, housewarmings, puberty and naming ceremonies, 60th "
            "birthdays), décor and design, venues and mandapams, catering, entertainment, concerts, "
            "festivals and cultural celebrations, exhibitions and trade shows, corporate events and "
            "MICE, brand activations, or event technology (drone and light shows, projection mapping, "
            "LED and media art, immersive experiences). False if events are not the main subject or "
            "the page has no real information (politics, crime, sports scores, job adverts, bare listings)."
        )
    )
    title: str = Field(description="Objective, concise, factual headline in English, no hype")
    entity_name: str = Field(description="Organiser, company, venue, festival or publication behind the news")
    primary_category: Literal[
        "Wedding",
        "Family Function",
        "Décor & Design",
        "Event Tech",
        "Corporate & MICE",
        "Concerts & Festivals",
        "Culture & Celebrations",
        "Industry News",
        "Tips & Trends",
        "Viral Moment",
    ]
    region: Literal["Tamil Nadu", "India", "Global", "East Asia", "Middle East"] = Field(
        description="Where the story happens: Tamil Nadu, India (rest of India), East Asia (China, Korea, "
        "Japan and nearby), Middle East (Gulf), else Global"
    )
    summary: str = Field(description="2-3 plain English sentences on what happened, facts from the text only")
    exact_source_quote: str = Field(
        description=(
            "MANDATORY: One complete sentence copied word-for-word from the provided text (in its "
            "original language) that proves the main claim. At least 40 characters."
        )
    )
    country_of_origin: Optional[str] = Field(default="Global", description="Country where it happened")
    hook_idea: str = Field(
        default="",
        description="A reel opening line (first 2 seconds) in Zenfest's voice for Tamil families, "
        "simple English or Tanglish, with no brand, celebrity, team or film names",
    )
    hook_score: int = Field(default=1, ge=1, le=5, description="How scroll-stopping the first 2 seconds can be")
    relevance_score: int = Field(default=1, ge=1, le=5, description="How useful to Tamil families planning events")
    visual_score: int = Field(default=1, ge=1, le=5, description="How well it can be shown with our own footage")
    evergreen: bool = Field(default=False, description="True for tips and lasting trends, False for dated news")
    brand_note: str = Field(
        default="",
        description="Names, logos, characters or people to keep OUT of the creative, and how to say it "
        "generically (e.g. 'say a Chinese drone company'). Empty if nothing.",
    )

    # The owner's feed in the website admin (2026-11-18): read like a friend explaining it.
    plain_headline: str = Field(
        default="",
        description="Headline in very simple English (max ~12 words), no jargon or trade words "
        "(say 'big business meeting', not 'MICE'), what happened, not hype",
    )
    plain_story: str = Field(
        default="",
        description="2-3 short sentences in very simple English: what happened, where, and why an "
        "event planner in Tamil Nadu should care. Explain any unusual word.",
    )
    example: str = Field(
        default="",
        description="One real-life example of how this would look in Tamil Nadu: a family's wedding, "
        "a Coimbatore reception, a Chennai office party, a valaikappu... 1-2 sentences, simple English, "
        "no real people's names",
    )

    @field_validator("hook_idea", "brand_note", "plain_headline", "plain_story", "example", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return v or ""
