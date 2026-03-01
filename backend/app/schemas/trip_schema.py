"""Trip request/response schemas.

Trip routes use these models to validate creation requests and dates.
"""

from pydantic import BaseModel, Field


class TripCreateSchema(BaseModel):
    """Trip shell metadata before itinerary/risk enrichment."""

    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=160)
    start_date: str
    end_date: str
