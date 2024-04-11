from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts and customer visits are all reset.
    """
    try:
        with db.engine.begin() as connection:
            # Reset global inventory
            connection.execute(sqlalchemy.text("""
                UPDATE global_inventory
                SET num_green_potions = 0, num_green_ml = 0, gold = 100
            """))

            connection.execute(sqlalchemy.text("""
                UPDATE capacity_inventory
                SET potion_capacity = 0, ml_capacity = 0
            """))

            connection.execute(sqlalchemy.text("""
                DELETE FROM customer_visits
            """))

            connection.execute(sqlalchemy.text("DELETE FROM cart_items"))
            connection.execute(sqlalchemy.text("DELETE FROM carts"))

        return {"status": "Game state reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))