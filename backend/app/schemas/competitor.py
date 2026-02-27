from datetime import datetime

from pydantic import BaseModel


class CompetitorOut(BaseModel):
    id: int
    name: str
    mosaic_brand: str
    facebook_page_id: str
    justification: str
    target_audience: str
    price_tier: str
    created_at: datetime

    model_config = {"from_attributes": True}
