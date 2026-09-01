from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import init_db
from app.routers import users, portfolio, personalization


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically initialize SQLite tables on application startup
    init_db()
    yield


app = FastAPI(
    title="Module 3: User Profile, Portfolio & Personalization Service",
    description="Microservice managing user profiles, dynamic portfolio concentration, watchlists, and personalization context for downstream multi-agent financial intelligence.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app.include_router(users.router)
app.include_router(portfolio.router)
app.include_router(personalization.router)
