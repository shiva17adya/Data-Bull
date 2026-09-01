# Module 3 — User Profile, Portfolio & Personalization Service

**Module 3** is an isolated, production-grade FastAPI microservice designed for the *Multi-Agent Autonomous Financial Intelligence System for Retail Investors*. It serves as the single source of truth for investor profiles, dynamic portfolio concentration analytics, watchlists, interaction logs, and personalized investment guidance.

---

## 1. What Module 3 Does

- **User Profile Management**: Stores user identification, risk tolerance (`conservative`, `moderate`, `aggressive`), and investment horizon years.
- **Dynamic Portfolio Valuation & Concentration**: Tracks equity holdings (quantity, average cost, current price) and dynamically calculates total portfolio value, percentage allocation per stock, largest position, top-3 concentration, and automated risk concentration flags. Position percentages are computed on the fly to prevent stale data.
- **Watchlist & Interaction Tracking**: Manages target tickers and interaction audit logs.
- **Personalization Engine**: Provides a clean, deterministic context provider for downstream synthesis agents. It computes risk sensitivity, position sensitivity, accumulation bias, and machine-friendly factors.
- **No Direct Trade Advice**: Never issues `BUY`, `SELL`, or `HOLD` recommendations. All decision synthesis is delegated to the Synthesis Layer.

---

## 2. Architecture & Design

```
                     ┌──────────────────────────────┐
                     │   Synthesis Layer / Engine   │
                     └──────────────┬───────────────┘
                                    │ HTTP GET /users/{user_id}/personalization/{symbol}
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                     MODULE 3                                           │
│                                                                                        │
│   FastAPI Application (app/main.py)                                                    │
│       ├── Health Router: GET /health                                                   │
│       ├── Users Router: /users (profiles, watchlists, interactions)                    │
│       ├── Portfolio Router: /users/{user_id}/portfolio & /holdings                     │
│       └── Personalization Router: /users/{user_id}/personalization/{symbol}            │
│                                                                                        │
│   Service Layer (app/services/)                                                        │
│       ├── profile_service.py: CRUD & constraints validation                            │
│       ├── portfolio_service.py: Dynamic valuation & concentration analytics            │
│       └── personalization_service.py: Deterministic rule-based guidance engine         │
│                                                                                        │
│   Persistence Layer (app/models.py & app/database.py)                                  │
│       └── SQLite Database (profile.db) via SQLAlchemy Session Dependency Injection     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
module3_profile/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── portfolio.py
│   │   └── personalization.py
│   └── services/
│       ├── __init__.py
│       ├── profile_service.py
│       ├── portfolio_service.py
│       └── personalization_service.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_users.py
│   ├── test_portfolio.py
│   ├── test_personalization.py
│   └── test_missing_user.py
│
├── seed.py
├── requirements.txt
├── README.md
├── .gitignore
└── profile.db
```

---

## 3. Installation

From `module3_profile/` or root:

```bash
cd module3_profile
pip install -r requirements.txt
```

---

## 4. Running the Service

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

When started:
- SQLite tables are automatically created in `./profile.db`.
- Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.
- Redoc is available at `http://localhost:8000/redoc`.

---

## 5. Running Seed Data

To populate the three standard demonstration personas (`user_001`, `user_002`, `user_003`), run:

```bash
python seed.py
```

*Note: The seeding script is fully idempotent. Running it multiple times safely resets the demo records without duplicate key errors.*

---

## 6. Running Tests

Run the complete test suite using pytest (isolated from `profile.db` using in-memory SQLite):

```bash
python -m pytest -v tests/
```

---

## 7. API Endpoints

| Category | Method | Endpoint | Description |
|---|---|---|---|
| **Health** | `GET` | `/health` | Service health check |
| **Users** | `POST` | `/users` | Create user profile (`201` created, `409` duplicate) |
| **Users** | `GET` | `/users/{user_id}` | Fetch user profile (`404` if not found) |
| **Users** | `PUT` | `/users/{user_id}` | Update risk tolerance / horizon (`404` if not found) |
| **Watchlist** | `POST` | `/users/{user_id}/watchlist` | Add symbol to watchlist (`201`, `409` duplicate) |
| **Watchlist** | `GET` | `/users/{user_id}/watchlist` | Get user watchlist (`404` if missing user) |
| **Interactions**| `POST` | `/users/{user_id}/interactions` | Log decision/interaction history |
| **Portfolio** | `POST` | `/users/{user_id}/holdings` | Add holding (`201`, `409` duplicate symbol) |
| **Portfolio** | `GET` | `/users/{user_id}/portfolio` | Dynamic portfolio valuation & holding allocations |
| **Portfolio** | `GET` | `/users/{user_id}/portfolio/risk` | Concentration level, top 3 %, largest position & risk flags |
| **Personalization** | `GET` | `/users/{user_id}/personalization/{symbol}` | Context & guidance payload for synthesis engine |

---

## 8. Example Requests & Responses

### 1. Create User
```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "risk_tolerance": "conservative", "investment_horizon_years": 10}'
```
**Response (201):**
```json
{
  "user_id": "user_001",
  "risk_tolerance": "conservative",
  "investment_horizon_years": 10
}
```

### 2. Add Holding
```bash
curl -X POST http://localhost:8000/users/user_001/holdings \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "quantity": 100, "average_price": 2500, "current_price": 2800}'
```
**Response (201):**
```json
{
  "message": "Holding added successfully",
  "user_id": "user_001",
  "symbol": "RELIANCE",
  "quantity": 100.0,
  "average_price": 2500.0,
  "current_price": 2800.0
}
```

### 3. Get Portfolio
```bash
curl -X GET http://localhost:8000/users/user_001/portfolio
```
**Response (200):**
```json
{
  "user_id": "user_001",
  "total_value": 640000.0,
  "holdings": [
    {
      "symbol": "RELIANCE",
      "quantity": 100.0,
      "average_price": 2500.0,
      "current_price": 2800.0,
      "value": 280000.0,
      "position_percentage": 43.75
    },
    {
      "symbol": "TCS",
      "quantity": 40.0,
      "average_price": 3000.0,
      "current_price": 3000.0,
      "value": 120000.0,
      "position_percentage": 18.75
    },
    {
      "symbol": "HDFCBANK",
      "quantity": 100.0,
      "average_price": 1500.0,
      "current_price": 1500.0,
      "value": 150000.0,
      "position_percentage": 23.44
    },
    {
      "symbol": "INFY",
      "quantity": 50.0,
      "average_price": 1800.0,
      "current_price": 1800.0,
      "value": 90000.0,
      "position_percentage": 14.06
    }
  ]
}
```

### 4. Get Personalization Context
```bash
curl -X GET http://localhost:8000/users/user_001/personalization/RELIANCE
```
**Response (200):**
```json
{
  "user_id": "user_001",
  "symbol": "RELIANCE",
  "profile": {
    "risk_tolerance": "conservative",
    "investment_horizon_years": 10
  },
  "portfolio_context": {
    "portfolio_value": 640000.0,
    "current_position_percentage": 43.75,
    "number_of_holdings": 4,
    "concentration_level": "high"
  },
  "watchlist": {
    "is_watchlisted": true
  },
  "personalization_factors": [
    "USER_IS_CONSERVATIVE",
    "HIGH_RELIANCE_EXPOSURE",
    "SINGLE_STOCK_CONCENTRATION",
    "SYMBOL_IS_WATCHLISTED"
  ],
  "personalization_guidance": {
    "risk_sensitivity": "high",
    "position_sensitivity": "high",
    "accumulation_bias": "cautious"
  }
}
```

---

## 9. Personalization & Concentration Logic

### Concentration Thresholds:
- `portfolio_value == 0` or 0 holdings: `none`
- Largest position `< 10%`: `low`
- `10% <=` Largest position `< 20%`: `moderate`
- `20% <=` Largest position `<= 30%`: `elevated`
- Largest position `> 30%`: `high`

### Risk Flags:
- Largest position `> 20%`: `HIGH_SINGLE_STOCK_CONCENTRATION`
- Largest position `> 30%`: `VERY_HIGH_SINGLE_STOCK_CONCENTRATION`
- `number_of_holdings == 1`: `LOW_DIVERSIFICATION`
- Top 3 concentration `> 60%`: `HIGH_TOP_3_CONCENTRATION`

### Personalization Guidance Rules:
1. **Risk Sensitivity**:
   - `conservative` &rarr; `high`
   - `moderate` &rarr; `medium`
   - `aggressive` &rarr; `low`
2. **Position Sensitivity**:
   - Symbol exposure `> 20%`: `high`
   - Symbol exposure between `10%` and `20%`: `medium`
   - Symbol exposure `< 10%` or not owned: `low`
3. **Accumulation Bias**:
   - `conservative` AND exposure `> 20%`: `cautious`
   - `aggressive` AND exposure `< 10%`: `willing`
   - `moderate`: `balanced`
   - Otherwise: `neutral`

---

## 10. How the Synthesis Layer Integrates With Module 3

The synthesis layer should treat Module 3 as an external personalization context provider.

### Integration Flow:
1. **Trigger**: Synthesis receives `user_id` and `symbol`.
2. **Agent Signals**: Synthesis obtains technical, fundamental, sentiment, and risk agent outputs from the other system components.
3. **Context Lookup**: Synthesis calls:
   ```http
   GET /users/{user_id}/personalization/{symbol}
   ```
4. **Context Ingestion**: Module 3 returns the user profile, portfolio exposure, concentration, watchlist status, personalization factors, and guidance.
5. **Multi-Signal Fusion**: Synthesis combines the raw agent outputs with this personalization context (e.g. if technical agent gives a bullish signal, but `accumulation_bias == "cautious"` and `HIGH_RELIANCE_EXPOSURE` is flagged, the synthesis layer dampens the recommendation size or advises risk-hedging).
6. **Output Delivery**: Synthesis produces the final user-facing recommendation.

> **CRITICAL RULE**: The synthesis layer must **NOT** access SQLite directly. All interactions with user profiles and portfolios must go through the Module 3 REST API.
