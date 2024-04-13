from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
import logging
from src import database as db
from pydantic import BaseModel
from src.api import auth

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
    try:
        with db.engine.begin() as connection:
            insert_query = sqlalchemy.text(
                "INSERT INTO game_time (day, hour) VALUES (:day, :hour)"
            )
            # Make sure parameters are correctly passed as a dictionary
            connection.execute(insert_query, {'day': timestamp.day, 'hour': timestamp.hour})
        return {"status": "Current time logged successfully."}
    except SQLAlchemyError as e:
        logging.error(f"SQLAlchemy Error when logging time: {e}")
        raise HTTPException(status_code=500, detail="Failed to log time due to database error.")
    except Exception as e:
        logging.error(f"Unexpected error when logging time: {e}")
        raise HTTPException(status_code=500, detail="Failed to log time due to an unexpected error.")
