def test_add_holding(client):
    client.post(
        "/users",
        json={
            "user_id": "port_user_1",
            "risk_tolerance": "moderate",
            "investment_horizon_years": 5,
        },
    )
    res = client.post(
        "/users/port_user_1/holdings",
        json={
            "symbol": "reliance",
            "quantity": 100,
            "average_price": 2500,
            "current_price": 2800,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["symbol"] == "RELIANCE"
    assert data["quantity"] == 100
    assert data["current_price"] == 2800


def test_calculate_portfolio_value_and_position_percentage(client):
    client.post(
        "/users",
        json={
            "user_id": "port_user_2",
            "risk_tolerance": "moderate",
            "investment_horizon_years": 5,
        },
    )
    # Holding 1: RELIANCE: 100 * 2800 = 280,000
    client.post(
        "/users/port_user_2/holdings",
        json={
            "symbol": "RELIANCE",
            "quantity": 100,
            "average_price": 2500,
            "current_price": 2800,
        },
    )
    # Holding 2: TCS: 40 * 3000 = 120,000
    client.post(
        "/users/port_user_2/holdings",
        json={
            "symbol": "TCS",
            "quantity": 40,
            "average_price": 3000,
            "current_price": 3000,
        },
    )
    # Total = 400,000
    # RELIANCE % = 280,000 / 400,000 * 100 = 70.0%
    # TCS % = 120,000 / 400,000 * 100 = 30.0%

    res = client.get("/users/port_user_2/portfolio")
    assert res.status_code == 200
    data = res.json()
    assert data["total_value"] == 400000.0
    assert len(data["holdings"]) == 2

    holdings_dict = {h["symbol"]: h for h in data["holdings"]}
    assert holdings_dict["RELIANCE"]["value"] == 280000.0
    assert holdings_dict["RELIANCE"]["position_percentage"] == 70.0
    assert holdings_dict["TCS"]["value"] == 120000.0
    assert holdings_dict["TCS"]["position_percentage"] == 30.0


def test_calculate_largest_position_and_top_3_concentration(client):
    client.post(
        "/users",
        json={
            "user_id": "port_user_3",
            "risk_tolerance": "conservative",
            "investment_horizon_years": 10,
        },
    )
    # 4 holdings
    # A: 40,000 (40%)
    # B: 30,000 (30%)
    # C: 20,000 (20%)
    # D: 10,000 (10%)
    # Total: 100,000
    # Top 3 concentration: 40 + 30 + 20 = 90.0%
    # Largest: A (40%)
    client.post("/users/port_user_3/holdings", json={"symbol": "STK_A", "quantity": 40, "average_price": 1000, "current_price": 1000})
    client.post("/users/port_user_3/holdings", json={"symbol": "STK_B", "quantity": 30, "average_price": 1000, "current_price": 1000})
    client.post("/users/port_user_3/holdings", json={"symbol": "STK_C", "quantity": 20, "average_price": 1000, "current_price": 1000})
    client.post("/users/port_user_3/holdings", json={"symbol": "STK_D", "quantity": 10, "average_price": 1000, "current_price": 1000})

    res = client.get("/users/port_user_3/portfolio/risk")
    assert res.status_code == 200
    data = res.json()
    assert data["portfolio_value"] == 100000.0
    assert data["number_of_holdings"] == 4
    assert data["largest_position"]["symbol"] == "STK_A"
    assert data["largest_position"]["percentage"] == 40.0
    assert data["top_3_concentration"] == 90.0
    assert data["concentration_level"] == "high"


def test_detect_high_concentration_and_risk_flags(client):
    client.post(
        "/users",
        json={
            "user_id": "port_user_4",
            "risk_tolerance": "conservative",
            "investment_horizon_years": 10,
        },
    )
    # Single holding: 100% concentration
    client.post("/users/port_user_4/holdings", json={"symbol": "SOLO", "quantity": 10, "average_price": 100, "current_price": 100})

    res = client.get("/users/port_user_4/portfolio/risk")
    assert res.status_code == 200
    data = res.json()
    assert data["concentration_level"] == "high"
    flags = data["risk_flags"]
    assert "HIGH_SINGLE_STOCK_CONCENTRATION" in flags
    assert "VERY_HIGH_SINGLE_STOCK_CONCENTRATION" in flags
    assert "LOW_DIVERSIFICATION" in flags
    assert "HIGH_TOP_3_CONCENTRATION" in flags


def test_handle_empty_portfolio(client):
    client.post(
        "/users",
        json={
            "user_id": "empty_user",
            "risk_tolerance": "moderate",
            "investment_horizon_years": 5,
        },
    )
    res_port = client.get("/users/empty_user/portfolio")
    assert res_port.status_code == 200
    port_data = res_port.json()
    assert port_data["total_value"] == 0.0
    assert port_data["holdings"] == []

    res_risk = client.get("/users/empty_user/portfolio/risk")
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert risk_data["portfolio_value"] == 0.0
    assert risk_data["number_of_holdings"] == 0
    assert risk_data["largest_position"] is None
    assert risk_data["top_3_concentration"] == 0.0
    assert risk_data["concentration_level"] == "none"
    assert risk_data["risk_flags"] == []


def test_prevent_duplicate_holding(client):
    client.post(
        "/users",
        json={
            "user_id": "dup_hold_user",
            "risk_tolerance": "aggressive",
            "investment_horizon_years": 3,
        },
    )
    res1 = client.post(
        "/users/dup_hold_user/holdings",
        json={
            "symbol": "INFY",
            "quantity": 10,
            "average_price": 1500,
            "current_price": 1600,
        },
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/users/dup_hold_user/holdings",
        json={
            "symbol": "infy",
            "quantity": 5,
            "average_price": 1550,
            "current_price": 1600,
        },
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]
