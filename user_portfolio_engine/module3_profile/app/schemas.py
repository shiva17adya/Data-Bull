from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# User Schemas
class UserCreate(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    risk_tolerance: Literal["conservative", "moderate", "aggressive"]
    investment_horizon_years: int = Field(..., gt=0, description="Investment horizon in years (must be > 0)")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("user_id cannot be empty")
        return v


class UserUpdate(BaseModel):
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = None
    investment_horizon_years: Optional[int] = Field(None, gt=0, description="Investment horizon in years (must be > 0)")


class UserResponse(BaseModel):
    user_id: str
    risk_tolerance: str
    investment_horizon_years: int

    model_config = ConfigDict(from_attributes=True)


# Holding Schemas
class HoldingCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    quantity: float = Field(..., ge=0, description="Quantity held (must be non-negative)")
    average_price: float = Field(..., ge=0, description="Average purchase price (must be non-negative)")
    current_price: float = Field(..., ge=0, description="Current market price (must be non-negative)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("symbol cannot be empty")
        return v


class HoldingResponse(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    value: float
    position_percentage: float


class PortfolioResponse(BaseModel):
    user_id: str
    total_value: float
    holdings: list[HoldingResponse]


class LargestPositionInfo(BaseModel):
    symbol: str
    percentage: float


class PortfolioRiskResponse(BaseModel):
    user_id: str
    portfolio_value: float
    number_of_holdings: int
    largest_position: Optional[LargestPositionInfo] = None
    top_3_concentration: float
    concentration_level: str
    risk_flags: list[str]


# Watchlist Schemas
class WatchlistCreate(BaseModel):
    symbol: str = Field(..., description="Stock symbol to add to watchlist")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("symbol cannot be empty")
        return v


class WatchlistResponse(BaseModel):
    user_id: str
    watchlist: list[str]


# Interaction Schemas
class InteractionCreate(BaseModel):
    symbol: Optional[str] = None
    action: str = Field(..., description="Action taken or context")
    reason: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            return v if v else None
        return None

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("action cannot be empty")
        return v


class InteractionResponse(BaseModel):
    id: int
    user_id: str
    symbol: Optional[str]
    action: str
    reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Personalization Schemas
class ProfileContext(BaseModel):
    risk_tolerance: str
    investment_horizon_years: int


class PortfolioContext(BaseModel):
    portfolio_value: float
    current_position_percentage: float
    number_of_holdings: int
    concentration_level: str


class WatchlistContext(BaseModel):
    is_watchlisted: bool


class PersonalizationGuidance(BaseModel):
    risk_sensitivity: str
    position_sensitivity: str
    accumulation_bias: str


class PersonalizationResponse(BaseModel):
    user_id: str
    symbol: str
    profile: ProfileContext
    portfolio_context: PortfolioContext
    watchlist: WatchlistContext
    personalization_factors: list[str]
    personalization_guidance: PersonalizationGuidance
