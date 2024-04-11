from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)

class Timestamp(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(timestamp: Timestamp):
    """
    Log the current time to the database.
    """
    try:
        with db.engine.begin() as connection:
            insert_query = sqlalchemy.text(
                "INSERT INTO game_time (day, hour) VALUES (:day, :hour)"
            )
            connection.execute(insert_query, day=timestamp.day, hour=timestamp.hour)
        return {"status": "Current time logged successfully."}
    except Exception as e:
        return {"error": str(e)}
