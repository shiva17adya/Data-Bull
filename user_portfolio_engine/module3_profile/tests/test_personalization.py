def test_user_001_conservative_high_exposure(client):
    # USER 001 style: conservative + ~25% RELIANCE exposure
    client.post(
        "/users",
        json={
            "user_id": "user_001_test",
            "risk_tolerance": "conservative",
            "investment_horizon_years": 10,
        },
    )
    # RELIANCE: 100 * 2500 = 250,000 (25% of 1,000,000)
    client.post(
        "/users/user_001_test/holdings",
        json={"symbol": "RELIANCE", "quantity": 100, "average_price": 2500, "current_price": 2500},
    )
    # OTHER: 750 * 1000 = 750,000 (75% of 1,000,000)
    client.post(
        "/users/user_001_test/holdings",
        json={"symbol": "OTHER", "quantity": 750, "average_price": 1000, "current_price": 1000},
    )
    # Watchlist
    client.post("/users/user_001_test/watchlist", json={"symbol": "RELIANCE"})

    res = client.get("/users/user_001_test/personalization/RELIANCE")
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "user_001_test"
    assert data["symbol"] == "RELIANCE"
    assert data["profile"]["risk_tolerance"] == "conservative"
    assert data["profile"]["investment_horizon_years"] == 10

    # Portfolio context
    assert data["portfolio_context"]["portfolio_value"] == 1000000.0
    assert data["portfolio_context"]["current_position_percentage"] == 25.0
    assert data["portfolio_context"]["number_of_holdings"] == 2
    assert data["watchlist"]["is_watchlisted"] is True

    # Guidance
    guidance = data["personalization_guidance"]
    assert guidance["risk_sensitivity"] == "high"
    assert guidance["position_sensitivity"] == "high"
    assert guidance["accumulation_bias"] == "cautious"

    # Factors
    factors = data["personalization_factors"]
    assert "USER_IS_CONSERVATIVE" in factors
    assert "HIGH_RELIANCE_EXPOSURE" in factors
    assert "SYMBOL_IS_WATCHLISTED" in factors

    # Ensure NO BUY/SELL/HOLD recommendation keys exist
    for forbidden_key in ["recommendation", "action_recommendation", "buy", "sell", "hold"]:
        assert forbidden_key not in data


def test_user_002_aggressive_low_exposure(client):
    # USER 002 style: aggressive + ~5% RELIANCE exposure
    client.post(
        "/users",
        json={
            "user_id": "user_002_test",
            "risk_tolerance": "aggressive",
            "investment_horizon_years": 3,
        },
    )
    # RELIANCE: 20 * 2500 = 50,000 (5% of 1,000,000)
    client.post(
        "/users/user_002_test/holdings",
        json={"symbol": "RELIANCE", "quantity": 20, "average_price": 2500, "current_price": 2500},
    )
    # OTHER: 950 * 1000 = 950,000 (95% of 1,000,000)
    client.post(
        "/users/user_002_test/holdings",
        json={"symbol": "OTHER", "quantity": 950, "average_price": 1000, "current_price": 1000},
    )
    client.post("/users/user_002_test/watchlist", json={"symbol": "RELIANCE"})

    res = client.get("/users/user_002_test/personalization/RELIANCE")
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == "user_002_test"
    assert data["symbol"] == "RELIANCE"
    assert data["profile"]["risk_tolerance"] == "aggressive"
    assert data["portfolio_context"]["current_position_percentage"] == 5.0

    guidance = data["personalization_guidance"]
    assert guidance["risk_sensitivity"] == "low"
    assert guidance["position_sensitivity"] == "low"
    assert guidance["accumulation_bias"] == "willing"

    factors = data["personalization_factors"]
    assert "USER_IS_AGGRESSIVE" in factors
    assert "SYMBOL_IS_WATCHLISTED" in factors
    assert "HIGH_RELIANCE_EXPOSURE" not in factors


def test_same_market_context_different_user_profiles_different_personalization(client):
    """
    Explicit test:
    SAME SYMBOL
    SAME MARKET CONTEXT (current price 2800)
    DIFFERENT USER PROFILE
    -> DIFFERENT PERSONALIZATION CONTEXT
    """
    # Create Conservative User
    client.post(
        "/users",
        json={"user_id": "u_cons", "risk_tolerance": "conservative", "investment_horizon_years": 10},
    )
    client.post(
        "/users/u_cons/holdings",
        json={"symbol": "RELIANCE", "quantity": 100, "average_price": 2500, "current_price": 2800},
    )
    client.post(
        "/users/u_cons/holdings",
        json={"symbol": "TCS", "quantity": 100, "average_price": 2800, "current_price": 2800},
    )

    # Create Aggressive User
    client.post(
        "/users",
        json={"user_id": "u_aggr", "risk_tolerance": "aggressive", "investment_horizon_years": 2},
    )
    client.post(
        "/users/u_aggr/holdings",
        json={"symbol": "RELIANCE", "quantity": 10, "average_price": 2500, "current_price": 2800},
    )
    client.post(
        "/users/u_aggr/holdings",
        json={"symbol": "TCS", "quantity": 200, "average_price": 2800, "current_price": 2800},
    )

    # Call personalization for the exact same symbol RELIANCE
    res_cons = client.get("/users/u_cons/personalization/RELIANCE")
    res_aggr = client.get("/users/u_aggr/personalization/RELIANCE")

    assert res_cons.status_code == 200
    assert res_aggr.status_code == 200

    cons_data = res_cons.json()
    aggr_data = res_aggr.json()

    # The inputs to market are identical (RELIANCE @ 2800)
    assert cons_data["symbol"] == aggr_data["symbol"] == "RELIANCE"

    # Contexts must differ significantly:
    assert cons_data["profile"]["risk_tolerance"] != aggr_data["profile"]["risk_tolerance"]
    assert cons_data["personalization_guidance"]["risk_sensitivity"] == "high"
    assert aggr_data["personalization_guidance"]["risk_sensitivity"] == "low"

    assert cons_data["personalization_guidance"]["position_sensitivity"] == "high"
    assert aggr_data["personalization_guidance"]["position_sensitivity"] == "low"

    assert cons_data["personalization_guidance"]["accumulation_bias"] == "cautious"
    assert aggr_data["personalization_guidance"]["accumulation_bias"] == "willing"

    assert "USER_IS_CONSERVATIVE" in cons_data["personalization_factors"]
    assert "USER_IS_AGGRESSIVE" in aggr_data["personalization_factors"]
