from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User, Watchlist, Interaction
from app.schemas import UserCreate, UserUpdate, InteractionCreate


def get_user(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return user


def create_user(db: Session, user_in: UserCreate) -> User:
    existing = db.query(User).filter(User.user_id == user_in.user_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{user_in.user_id}' already exists",
        )
    
    user = User(
        user_id=user_in.user_id,
        risk_tolerance=user_in.risk_tolerance,
        investment_horizon_years=user_in.investment_horizon_years,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: str, user_in: UserUpdate) -> User:
    user = get_user(db, user_id)
    
    updated = False
    if user_in.risk_tolerance is not None:
        user.risk_tolerance = user_in.risk_tolerance
        updated = True
    if user_in.investment_horizon_years is not None:
        user.investment_horizon_years = user_in.investment_horizon_years
        updated = True
        
    if updated:
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        
    return user


def add_watchlist_symbol(db: Session, user_id: str, symbol: str) -> Watchlist:
    # Ensure user exists
    get_user(db, user_id)
    
    symbol_norm = symbol.strip().upper()
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol_norm)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Symbol '{symbol_norm}' already in watchlist for user '{user_id}'",
        )
        
    item = Watchlist(user_id=user_id, symbol=symbol_norm)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_watchlist(db: Session, user_id: str) -> list[str]:
    # Ensure user exists
    get_user(db, user_id)
    
    items = (
        db.query(Watchlist.symbol)
        .filter(Watchlist.user_id == user_id)
        .all()
    )
    return [item[0] for item in items]


def is_symbol_in_watchlist(db: Session, user_id: str, symbol: str) -> bool:
    symbol_norm = symbol.strip().upper()
    exists = (
        db.query(Watchlist.id)
        .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol_norm)
        .first()
    )
    return exists is not None


def record_interaction(
    db: Session, user_id: str, interaction_in: InteractionCreate
) -> Interaction:
    # Ensure user exists
    get_user(db, user_id)
    
    interaction = Interaction(
        user_id=user_id,
        symbol=interaction_in.symbol,
        action=interaction_in.action,
        reason=interaction_in.reason,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction
