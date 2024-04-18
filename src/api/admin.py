from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
import logging

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    try:
        with db.engine.begin() as connection:
            # Reset global inventory to initial state
            connection.execute(sqlalchemy.text("""
                UPDATE global_inventory SET
                num_green_potions = 0,
                num_green_ml = 0,
                num_red_potions = 0,
                num_red_ml = 0,
                num_blue_potions = 0,
                num_blue_ml = 0,
                gold = 100
            """))


            # Reset capacity inventory to its initial state
            connection.execute(sqlalchemy.text("""
                UPDATE capacity_inventory SET
                potion_capacity = 50,  -- Assuming initial capacity for green potions
                ml_capacity = 10000          -- Assuming initial total capacity for ml
                WHERE id = 1  -- Assuming you are updating the first row
            """))


            # Clear any customer visit logs
            connection.execute(sqlalchemy.text("DELETE FROM customer_visits"))

            # Optionally, reset any other tables such as carts or cart items if they exist
            connection.execute(sqlalchemy.text("DELETE FROM carts"))
            connection.execute(sqlalchemy.text("DELETE FROM cart_items"))

            logging.info("Game state has been reset successfully.")
        return {"status": "Game state reset successfully."}
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Database error during reset: {e}")
        raise HTTPException(status_code=500, detail="Database error during reset.")
    except Exception as e:
        logging.error(f"Unexpected error during reset: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during reset.")
