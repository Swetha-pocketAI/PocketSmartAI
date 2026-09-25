from typing import Literal
from pydantic import BaseModel, Field, model_validator

class HomeInput(BaseModel):
    budget: int = Field(ge=500, le=10000000)
    room: Literal['Living room', 'Bedroom', 'Kitchen']
    style: str = Field(min_length=2, max_length=60)
    lights: int = Field(ge=0, le=20)
    fans: int = Field(ge=0, le=10)
    tables: int = Field(ge=0, le=10)
    @model_validator(mode='after')
    def items_required(self):
        if not (self.lights + self.fans + self.tables):
            raise ValueError('Choose at least one item')
        return self

class PartyInput(BaseModel):
    budget: int = Field(ge=500, le=10000000)
    guests: int = Field(ge=1, le=5000)
    event_type: Literal['Birthday', 'Wedding', 'Corporate', 'Other']
    venue: Literal['Home', 'External']
    city: str = Field(min_length=2, max_length=80)

class JewelryInput(BaseModel):
    budget: int = Field(ge=500, le=10000000)
    occasion: Literal['Wedding', 'Party', 'Everyday', 'Festival']
    style: str = Field(min_length=2, max_length=60)
    outfit_color: str = Field(default='', max_length=60)

class Item(BaseModel):
    category: str
    name: str
    platform: str
    quantity: int
    unit_price: int
    subtotal: int
    search_url: str

class Plan(BaseModel):
    id: int | None = None
    kind: Literal['home', 'party', 'jewelry']
    budget: int
    total: int
    remaining: int
    items: list[Item]
    notes: list[str]
    insight: str
    source: Literal['demo', 'demo+gemini']
