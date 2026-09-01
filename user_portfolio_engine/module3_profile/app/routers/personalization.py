from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PersonalizationResponse
from app.services import personalization_service

router = APIRouter(prefix="/users/{user_id}", tags=["Personalization"])


@router.get("/personalization/{symbol}", response_model=PersonalizationResponse)
def get_personalization_endpoint(
    user_id: str, symbol: str, db: Session = Depends(get_db)
):
    return personalization_service.get_personalization_context(db, user_id, symbol)
