from sqlalchemy.orm import Session

from app.schemas import (
    PersonalizationResponse,
    ProfileContext,
    PortfolioContext,
    WatchlistContext,
    PersonalizationGuidance,
)
from app.services.profile_service import get_user, is_symbol_in_watchlist
from app.services.portfolio_service import calculate_portfolio, calculate_portfolio_risk


def get_personalization_context(
    db: Session, user_id: str, symbol: str
) -> PersonalizationResponse:
    # 1. Fetch user (404 if not found)
    user = get_user(db, user_id)
    symbol_norm = symbol.strip().upper()

    # 2. Fetch portfolio & risk calculations
    portfolio = calculate_portfolio(db, user_id)
    risk_metrics = calculate_portfolio_risk(db, user_id)

    # 3. Find target symbol exposure
    target_holding = next(
        (h for h in portfolio.holdings if h.symbol == symbol_norm), None
    )
    user_owns_symbol = target_holding is not None and target_holding.quantity > 0
    exposure = target_holding.position_percentage if user_owns_symbol else 0.0

    # 4. Check watchlist status
    is_watchlisted = is_symbol_in_watchlist(db, user_id, symbol_norm)

    # 5. Determine Risk Sensitivity
    risk_tol = user.risk_tolerance.lower()
    if risk_tol == "conservative":
        risk_sensitivity = "high"
    elif risk_tol == "moderate":
        risk_sensitivity = "medium"
    elif risk_tol == "aggressive":
        risk_sensitivity = "low"
    else:
        risk_sensitivity = "medium"

    # 6. Determine Position Sensitivity
    if not user_owns_symbol:
        position_sensitivity = "low"
    elif exposure > 20.0:
        position_sensitivity = "high"
    elif 10.0 <= exposure <= 20.0:
        position_sensitivity = "medium"
    else:
        position_sensitivity = "low"

    # 7. Determine Accumulation Bias
    if risk_tol == "conservative" and exposure > 20.0:
        accumulation_bias = "cautious"
    elif risk_tol == "aggressive" and exposure < 10.0:
        accumulation_bias = "willing"
    elif risk_tol == "moderate":
        accumulation_bias = "balanced"
    else:
        accumulation_bias = "neutral"

    # 8. Generate Personalization Factors
    factors: list[str] = []
    if risk_tol == "conservative":
        factors.append("USER_IS_CONSERVATIVE")
    elif risk_tol == "moderate":
        factors.append("USER_IS_MODERATE")
    elif risk_tol == "aggressive":
        factors.append("USER_IS_AGGRESSIVE")

    if exposure > 20.0:
        factors.append(f"HIGH_{symbol_norm}_EXPOSURE")

    if risk_metrics.concentration_level in ("elevated", "high"):
        factors.append("SINGLE_STOCK_CONCENTRATION")

    if is_watchlisted:
        factors.append("SYMBOL_IS_WATCHLISTED")

    if not user_owns_symbol:
        factors.append("NO_CURRENT_POSITION")

    return PersonalizationResponse(
        user_id=user.user_id,
        symbol=symbol_norm,
        profile=ProfileContext(
            risk_tolerance=user.risk_tolerance,
            investment_horizon_years=user.investment_horizon_years,
        ),
        portfolio_context=PortfolioContext(
            portfolio_value=portfolio.total_value,
            current_position_percentage=exposure,
            number_of_holdings=len(portfolio.holdings),
            concentration_level=risk_metrics.concentration_level,
        ),
        watchlist=WatchlistContext(is_watchlisted=is_watchlisted),
        personalization_factors=factors,
        personalization_guidance=PersonalizationGuidance(
            risk_sensitivity=risk_sensitivity,
            position_sensitivity=position_sensitivity,
            accumulation_bias=accumulation_bias,
        ),
    )
