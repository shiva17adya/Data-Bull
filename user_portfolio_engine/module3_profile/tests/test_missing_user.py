def test_missing_user_endpoints_return_404(client):
    endpoints = [
        ("GET", "/users/nonexistent"),
        ("GET", "/users/nonexistent/portfolio"),
        ("GET", "/users/nonexistent/portfolio/risk"),
        ("GET", "/users/nonexistent/personalization/RELIANCE"),
        ("GET", "/users/nonexistent/watchlist"),
    ]

    for method, url in endpoints:
        if method == "GET":
            res = client.get(url)
            assert res.status_code == 404, f"Expected 404 for {url}, got {res.status_code}"
            data = res.json()
            assert "detail" in data
            assert "nonexistent" in data["detail"]
            assert "not found" in data["detail"].lower()


def test_missing_user_mutation_endpoints_return_404(client):
    res_holding = client.post(
        "/users/nonexistent/holdings",
        json={
            "symbol": "RELIANCE",
            "quantity": 10,
            "average_price": 2500,
            "current_price": 2800,
        },
    )
    assert res_holding.status_code == 404
    assert "not found" in res_holding.json()["detail"].lower()

    res_watchlist = client.post(
        "/users/nonexistent/watchlist",
        json={"symbol": "RELIANCE"},
    )
    assert res_watchlist.status_code == 404
    assert "not found" in res_watchlist.json()["detail"].lower()

    res_interaction = client.post(
        "/users/nonexistent/interactions",
        json={"symbol": "RELIANCE", "action": "buy"},
    )
    assert res_interaction.status_code == 404
    assert "not found" in res_interaction.json()["detail"].lower()
