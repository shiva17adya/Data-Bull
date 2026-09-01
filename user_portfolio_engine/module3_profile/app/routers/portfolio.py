from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import HoldingCreate, PortfolioResponse, PortfolioRiskResponse
from app.services import portfolio_service

router = APIRouter(prefix="/users/{user_id}", tags=["Portfolio"])


@router.post("/holdings", status_code=status.HTTP_201_CREATED)
def add_holding_endpoint(
    user_id: str, holding_in: HoldingCreate, db: Session = Depends(get_db)
):
    holding = portfolio_service.add_holding(db, user_id, holding_in)
    return {
        "message": "Holding added successfully",
        "user_id": user_id,
        "symbol": holding.symbol,
        "quantity": holding.quantity,
        "average_price": holding.average_price,
        "current_price": holding.current_price,
    }


@router.get("/portfolio", response_model=PortfolioResponse)
def get_portfolio_endpoint(user_id: str, db: Session = Depends(get_db)):
    return portfolio_service.calculate_portfolio(db, user_id)


@router.get("/portfolio/risk", response_model=PortfolioRiskResponse)
def get_portfolio_risk_endpoint(user_id: str, db: Session = Depends(get_db)):
    return portfolio_service.calculate_portfolio_risk(db, user_id)
