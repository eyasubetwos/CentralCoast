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

class GameTime(BaseModel):
    day: str
    hour: int

@router.post("/current_time")
def post_time(game_time: GameTime):
    """
    Logs the current time to the database in a table designed to store such logs.
    """
    try:
        with db.engine.begin() as connection:
            insert_query = sqlalchemy.text(
                "INSERT INTO game_time (day, hour) VALUES (:day, :hour)"
            )
            connection.execute(insert_query, day=game_time.day, hour=game_time.hour)
        return {"status": "Current time logged successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


