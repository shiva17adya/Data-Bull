from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    WatchlistCreate,
    WatchlistResponse,
    InteractionCreate,
    InteractionResponse,
)
from app.services import profile_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(user_in: UserCreate, db: Session = Depends(get_db)):
    return profile_service.create_user(db, user_in)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(user_id: str, db: Session = Depends(get_db)):
    return profile_service.get_user(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: str, user_in: UserUpdate, db: Session = Depends(get_db)
):
    return profile_service.update_user(db, user_id, user_in)


@router.post("/{user_id}/watchlist", status_code=status.HTTP_201_CREATED)
def add_watchlist_symbol_endpoint(
    user_id: str, watchlist_in: WatchlistCreate, db: Session = Depends(get_db)
):
    item = profile_service.add_watchlist_symbol(db, user_id, watchlist_in.symbol)
    return {"user_id": user_id, "symbol": item.symbol, "message": "Symbol added to watchlist"}


@router.get("/{user_id}/watchlist", response_model=WatchlistResponse)
def get_watchlist_endpoint(user_id: str, db: Session = Depends(get_db)):
    symbols = profile_service.get_watchlist(db, user_id)
    return WatchlistResponse(user_id=user_id, watchlist=symbols)


@router.post(
    "/{user_id}/interactions",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_interaction_endpoint(
    user_id: str, interaction_in: InteractionCreate, db: Session = Depends(get_db)
):
    return profile_service.record_interaction(db, user_id, interaction_in)
