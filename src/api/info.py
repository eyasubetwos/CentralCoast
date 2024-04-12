from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):  # Ensure this class is defined correctly
    day: str
    hour: int


@router.post("/current_time")
def post_time(timestamp: Timestamp):
    try:
        with db.engine.begin() as connection:
            insert_query = sqlalchemy.text(
                "INSERT INTO game_time (day, hour) VALUES (:day, :hour)"
            )
            connection.execute(insert_query, day=timestamp.day, hour=timestamp.hour)
        return {"status": "Current time logged successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log time: {str(e)}")