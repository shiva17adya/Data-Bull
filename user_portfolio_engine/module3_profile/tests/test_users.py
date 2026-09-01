def test_create_user(client):
    response = client.post(
        "/users",
        json={
            "user_id": "test_user_1",
            "risk_tolerance": "conservative",
            "investment_horizon_years": 10,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == "test_user_1"
    assert data["risk_tolerance"] == "conservative"
    assert data["investment_horizon_years"] == 10


def test_get_user(client):
    client.post(
        "/users",
        json={
            "user_id": "test_user_2",
            "risk_tolerance": "moderate",
            "investment_horizon_years": 5,
        },
    )
    response = client.get("/users/test_user_2")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user_2"
    assert data["risk_tolerance"] == "moderate"
    assert data["investment_horizon_years"] == 5


def test_update_user(client):
    client.post(
        "/users",
        json={
            "user_id": "test_user_3",
            "risk_tolerance": "conservative",
            "investment_horizon_years": 10,
        },
    )
    response = client.put(
        "/users/test_user_3",
        json={
            "risk_tolerance": "aggressive",
            "investment_horizon_years": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_tolerance"] == "aggressive"
    assert data["investment_horizon_years"] == 3


def test_duplicate_user_returns_409(client):
    payload = {
        "user_id": "duplicate_user",
        "risk_tolerance": "conservative",
        "investment_horizon_years": 5,
    }
    res1 = client.post("/users", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/users", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_invalid_risk_tolerance_rejected(client):
    response = client.post(
        "/users",
        json={
            "user_id": "invalid_user",
            "risk_tolerance": "ultra_extreme",
            "investment_horizon_years": 5,
        },
    )
    assert response.status_code == 422


def test_invalid_investment_horizon_rejected(client):
    response = client.post(
        "/users",
        json={
            "user_id": "invalid_user_2",
            "risk_tolerance": "moderate",
            "investment_horizon_years": 0,
        },
    )
    assert response.status_code == 422
