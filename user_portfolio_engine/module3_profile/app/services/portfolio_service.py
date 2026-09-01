from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Holding
from app.schemas import (
    HoldingCreate,
    HoldingResponse,
    PortfolioResponse,
    PortfolioRiskResponse,
    LargestPositionInfo,
)
from app.services.profile_service import get_user


def add_holding(db: Session, user_id: str, holding_in: HoldingCreate) -> Holding:
    # Ensure user exists (raises 404 if not found)
    get_user(db, user_id)
    
    symbol_norm = holding_in.symbol.strip().upper()
    existing = (
        db.query(Holding)
        .filter(Holding.user_id == user_id, Holding.symbol == symbol_norm)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Holding for symbol '{symbol_norm}' already exists for user '{user_id}'",
        )
        
    holding = Holding(
        user_id=user_id,
        symbol=symbol_norm,
        quantity=holding_in.quantity,
        average_price=holding_in.average_price,
        current_price=holding_in.current_price,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding


def get_holdings_for_user(db: Session, user_id: str) -> list[Holding]:
    # Ensure user exists (raises 404 if not found)
    get_user(db, user_id)
    return db.query(Holding).filter(Holding.user_id == user_id).all()


def calculate_portfolio(db: Session, user_id: str) -> PortfolioResponse:
    # Ensure user exists
    get_user(db, user_id)
    holdings = db.query(Holding).filter(Holding.user_id == user_id).all()
    
    # Calculate position values
    calc_data = []
    total_value = 0.0
    for h in holdings:
        pos_val = round(h.quantity * h.current_price, 2)
        total_value += pos_val
        calc_data.append((h, pos_val))
        
    total_value = round(total_value, 2)
    
    holding_responses: list[HoldingResponse] = []
    for h, pos_val in calc_data:
        if total_value > 0:
            pos_pct = round((pos_val / total_value) * 100, 2)
        else:
            pos_pct = 0.0
            
        holding_responses.append(
            HoldingResponse(
                symbol=h.symbol,
                quantity=h.quantity,
                average_price=round(h.average_price, 2),
                current_price=round(h.current_price, 2),
                value=pos_val,
                position_percentage=pos_pct,
            )
        )
        
    return PortfolioResponse(
        user_id=user_id,
        total_value=total_value,
        holdings=holding_responses,
    )


def calculate_portfolio_risk(db: Session, user_id: str) -> PortfolioRiskResponse:
    # Ensure user exists
    get_user(db, user_id)
    portfolio = calculate_portfolio(db, user_id)
    
    number_of_holdings = len(portfolio.holdings)
    portfolio_value = portfolio.total_value
    
    if number_of_holdings == 0 or portfolio_value == 0:
        return PortfolioRiskResponse(
            user_id=user_id,
            portfolio_value=portfolio_value,
            number_of_holdings=number_of_holdings,
            largest_position=None,
            top_3_concentration=0.0,
            concentration_level="none",
            risk_flags=[],
        )
        
    # Sort holdings by position_percentage descending
    sorted_holdings = sorted(
        portfolio.holdings, key=lambda h: h.position_percentage, reverse=True
    )
    
    largest = sorted_holdings[0]
    largest_position = LargestPositionInfo(
        symbol=largest.symbol,
        percentage=largest.position_percentage,
    )
    
    top_3_concentration = round(
        sum(h.position_percentage for h in sorted_holdings[:3]), 2
    )
    
    # Concentration level
    # largest position < 10%: "low"
    # 10% <= largest position < 20%: "moderate"
    # 20% <= largest position <= 30%: "elevated"
    # largest position > 30%: "high"
    lp_pct = largest.position_percentage
    if lp_pct < 10.0:
        concentration_level = "low"
    elif lp_pct < 20.0:
        concentration_level = "moderate"
    elif lp_pct <= 30.0:
        concentration_level = "elevated"
    else:
        concentration_level = "high"
        
    # Risk flags
    # If largest position > 20%: "HIGH_SINGLE_STOCK_CONCENTRATION"
    # If largest position > 30%: "VERY_HIGH_SINGLE_STOCK_CONCENTRATION"
    # If number of holdings == 1: "LOW_DIVERSIFICATION"
    # If top_3_concentration > 60%: "HIGH_TOP_3_CONCENTRATION"
    risk_flags: list[str] = []
    if lp_pct > 20.0:
        risk_flags.append("HIGH_SINGLE_STOCK_CONCENTRATION")
    if lp_pct > 30.0:
        risk_flags.append("VERY_HIGH_SINGLE_STOCK_CONCENTRATION")
    if number_of_holdings == 1:
        risk_flags.append("LOW_DIVERSIFICATION")
    if top_3_concentration > 60.0:
        risk_flags.append("HIGH_TOP_3_CONCENTRATION")
        
    # Avoid duplicate risk flags while maintaining order
    unique_risk_flags = list(dict.fromkeys(risk_flags))
    
    return PortfolioRiskResponse(
        user_id=user_id,
        portfolio_value=portfolio_value,
        number_of_holdings=number_of_holdings,
        largest_position=largest_position,
        top_3_concentration=top_3_concentration,
        concentration_level=concentration_level,
        risk_flags=unique_risk_flags,
    )
