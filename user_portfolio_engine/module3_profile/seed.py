import os
import sys

# Ensure module directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import User, Holding, Watchlist, Interaction


def seed_demo_users():
    """Idempotently seed demo users and their portfolios."""
    init_db()
    db = SessionLocal()
    try:
        demo_user_ids = ["user_001", "user_002", "user_003"]
        
        # Clean existing demo records to ensure idempotency
        for uid in demo_user_ids:
            db.query(Holding).filter(Holding.user_id == uid).delete()
            db.query(Watchlist).filter(Watchlist.user_id == uid).delete()
            db.query(Interaction).filter(Interaction.user_id == uid).delete()
            db.query(User).filter(User.user_id == uid).delete()
        db.commit()

        # -------------------------------------------------------------
        # USER 001: Conservative, 10 years, High RELIANCE exposure
        # -------------------------------------------------------------
        user_1 = User(
            user_id="user_001",
            risk_tolerance="conservative",
            investment_horizon_years=10,
        )
        db.add(user_1)
        db.commit()

        user_1_holdings = [
            Holding(user_id="user_001", symbol="RELIANCE", quantity=100, average_price=2500, current_price=2800),
            Holding(user_id="user_001", symbol="TCS", quantity=40, average_price=3000, current_price=3000),
            Holding(user_id="user_001", symbol="HDFCBANK", quantity=100, average_price=1500, current_price=1500),
            Holding(user_id="user_001", symbol="INFY", quantity=50, average_price=1800, current_price=1800),
        ]
        db.add_all(user_1_holdings)

        user_1_watchlist = [
            Watchlist(user_id="user_001", symbol="RELIANCE"),
            Watchlist(user_id="user_001", symbol="TCS"),
        ]
        db.add_all(user_1_watchlist)

        # -------------------------------------------------------------
        # USER 002: Aggressive, 3 years, Low RELIANCE exposure (~5%)
        # -------------------------------------------------------------
        user_2 = User(
            user_id="user_002",
            risk_tolerance="aggressive",
            investment_horizon_years=3,
        )
        db.add(user_2)
        db.commit()

        user_2_holdings = [
            Holding(user_id="user_002", symbol="RELIANCE", quantity=10, average_price=2500, current_price=2800), # 28,000
            Holding(user_id="user_002", symbol="TCS", quantity=50, average_price=3000, current_price=3000),      # 150,000
            Holding(user_id="user_002", symbol="HDFCBANK", quantity=100, average_price=1500, current_price=1500),# 150,000
            Holding(user_id="user_002", symbol="INFY", quantity=80, average_price=1800, current_price=1800),     # 144,000
            Holding(user_id="user_002", symbol="ICICIBANK", quantity=100, average_price=950, current_price=1000),# 100,000
        ]
        db.add_all(user_2_holdings)

        user_2_watchlist = [
            Watchlist(user_id="user_002", symbol="RELIANCE"),
        ]
        db.add_all(user_2_watchlist)

        # -------------------------------------------------------------
        # USER 003: Moderate, 7 years, Moderate RELIANCE exposure (10-15%)
        # -------------------------------------------------------------
        user_3 = User(
            user_id="user_003",
            risk_tolerance="moderate",
            investment_horizon_years=7,
        )
        db.add(user_3)
        db.commit()

        user_3_holdings = [
            Holding(user_id="user_003", symbol="RELIANCE", quantity=25, average_price=2600, current_price=2800), # 70,000 (~13.8%)
            Holding(user_id="user_003", symbol="TCS", quantity=40, average_price=3000, current_price=3000),      # 120,000
            Holding(user_id="user_003", symbol="HDFCBANK", quantity=100, average_price=1500, current_price=1500),# 150,000
            Holding(user_id="user_003", symbol="INFY", quantity=60, average_price=1800, current_price=1800),     # 108,000
            Holding(user_id="user_003", symbol="ICICIBANK", quantity=60, average_price=950, current_price=1000), # 60,000
        ]
        db.add_all(user_3_holdings)

        user_3_watchlist = [
            Watchlist(user_id="user_003", symbol="RELIANCE"),
            Watchlist(user_id="user_003", symbol="TCS"),
            Watchlist(user_id="user_003", symbol="INFY"),
        ]
        db.add_all(user_3_watchlist)

        # Optional sample interaction
        interaction = Interaction(
            user_id="user_001",
            symbol="RELIANCE",
            action="hold",
            reason="High portfolio concentration",
        )
        db.add(interaction)

        db.commit()
        print("Demo users successfully seeded (user_001, user_002, user_003).")
    except Exception as e:
        db.rollback()
        print(f"Error seeding demo users: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_users()
