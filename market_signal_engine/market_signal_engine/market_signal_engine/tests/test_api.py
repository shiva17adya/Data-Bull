"""API-level tests. These assert the contract downstream teammates depend on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import SERVICE_NAME
from app.main import app

client = TestClient(app)

REQUIRED_TOP_LEVEL_FIELDS = {
    "symbol",
    "timestamp",
    "market_data",
    "signals",
    "overall_signal",
    "confidence",
    "reasoning",
    "data_status",
    "warnings",
}

REQUIRED_SIGNAL_FIELDS = {"name", "signal", "value", "confidence", "evidence"}
VALID_LABELS = {"BULLISH", "NEUTRAL", "BEARISH", "UNAVAILABLE"}


def test_health_returns_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": SERVICE_NAME}


def test_market_endpoint_returns_ohlcv():
    response = client.get("/market/RELIANCE")
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "RELIANCE"
    assert body["data_status"] == "OK"
    assert body["candle_count"] > 0

    market = body["market_data"]
    for field in ("price", "open", "high", "low", "close", "volume", "currency"):
        assert field in market
    assert market["price"] > 0
    assert market["currency"] == "INR"


@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY", "HDFCBANK"])
def test_signals_endpoint_contract(symbol):
    response = client.get(f"/signals/{symbol}")
    assert response.status_code == 200
    body = response.json()

    assert REQUIRED_TOP_LEVEL_FIELDS.issubset(body)
    assert body["symbol"] == symbol
    assert body["overall_signal"] in {"BULLISH", "NEUTRAL", "BEARISH"}
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["data_status"] in {"OK", "DEGRADED", "UNAVAILABLE"}
    assert isinstance(body["reasoning"], list) and body["reasoning"]
    assert isinstance(body["warnings"], list)

    signals = body["signals"]
    assert set(signals) == {"price_momentum", "volume_anomaly", "rsi"}
    for name, signal in signals.items():
        assert REQUIRED_SIGNAL_FIELDS.issubset(signal)
        assert signal["name"] == name
        assert signal["signal"] in VALID_LABELS
        assert 0.0 <= signal["confidence"] <= 1.0
        assert isinstance(signal["evidence"], list) and signal["evidence"]


def test_lowercase_symbol_is_accepted():
    response = client.get("/signals/reliance")
    assert response.status_code == 200
    assert response.json()["symbol"] == "RELIANCE"


def test_unknown_symbol_returns_clean_404():
    response = client.get("/signals/RELIANCE_X")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SYMBOL_NOT_FOUND"
    assert "RELIANCE_X" in body["error"]["message"]
    assert "Traceback" not in response.text


def test_unknown_symbol_on_market_endpoint_returns_404():
    response = client.get("/market/NOPE")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SYMBOL_NOT_FOUND"


@pytest.mark.parametrize("value", ["0", "-3", "999", "abc"])
def test_invalid_lookback_returns_structured_error(value):
    response = client.get(f"/signals/RELIANCE?lookback={value}")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert "Traceback" not in response.text


def test_valid_lookback_query_parameter_is_applied():
    short = client.get("/signals/RELIANCE?lookback=2").json()
    long = client.get("/signals/RELIANCE?lookback=30").json()
    assert short["signals"]["price_momentum"]["value"] != (
        long["signals"]["price_momentum"]["value"]
    )


def test_degraded_response_is_still_a_valid_200():
    response = client.get("/signals/DEMO_NOVOLUME")
    assert response.status_code == 200
    body = response.json()
    assert body["data_status"] == "DEGRADED"
    assert body["signals"]["volume_anomaly"]["signal"] == "UNAVAILABLE"
    assert body["signals"]["volume_anomaly"]["value"] is None
    assert body["warnings"]


def test_short_history_response_is_degraded_not_an_error():
    response = client.get("/signals/DEMO_SHORTHIST")
    assert response.status_code == 200
    assert response.json()["data_status"] == "DEGRADED"


def test_corrupt_data_response_is_degraded_not_an_error():
    response = client.get("/signals/DEMO_CORRUPT")
    assert response.status_code == 200
    assert response.json()["data_status"] == "DEGRADED"


def test_symbols_endpoint_lists_supported_symbols():
    response = client.get("/symbols")
    assert response.status_code == 200
    symbols = response.json()
    for expected in ("RELIANCE", "TCS", "INFY", "HDFCBANK"):
        assert expected in symbols


def test_openapi_schema_is_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/signals/{symbol}" in schema["paths"]
    assert "SignalResponse" in schema["components"]["schemas"]


def test_docs_endpoint_renders():
    response = client.get("/docs")
    assert response.status_code == 200


def test_repeated_requests_return_identical_signals():
    first = client.get("/signals/RELIANCE").json()
    second = client.get("/signals/RELIANCE").json()
    assert first["signals"] == second["signals"]
    assert first["overall_signal"] == second["overall_signal"]
    assert first["confidence"] == second["confidence"]


def test_response_language_avoids_investment_advice():
    """The module reports signals, never instructions to trade."""
    text = client.get("/signals/RELIANCE").text.lower()
    for forbidden in ("buy this", "sell this", "guaranteed", "will rise", "you should"):
        assert forbidden not in text
