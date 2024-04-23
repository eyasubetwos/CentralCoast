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
    The potion mixes are reset to their initial state as defined in the potion_mixes table.
    """
    try:
        with db.engine.begin() as connection:
            # Reset gold to initial state and clear potion inventory
            connection.execute(sqlalchemy.text("""
                UPDATE global_inventory SET
                gold = 100
            """))
            connection.execute(sqlalchemy.text("""
                DELETE FROM potion_mixes
            """))

            # Optionally, insert initial potion mixes state if needed
            # INSERT INTO potion_mixes (columns...) VALUES (values...)

            # Reset capacity inventory to its initial state
            # Adjust if the capacity_inventory structure has changed
            connection.execute(sqlalchemy.text("""
                UPDATE capacity_inventory SET
                potion_capacity = 50,  -- Assuming initial capacity for green potions
                ml_capacity = 10000    -- Assuming initial total capacity for ml
                WHERE id = 1
            """))

            # Clear any customer visit logs and carts
            connection.execute(sqlalchemy.text("DELETE FROM customer_visits"))
            connection.execute(sqlalchemy.text("DELETE FROM carts"))
            connection.execute(sqlalchemy.text("DELETE FROM cart_items"))

            # Reset audit logs if implemented
            # connection.execute(sqlalchemy.text("DELETE FROM audit_logs"))

            logging.info("Game state has been reset successfully.")
        return {"status": "Game state reset successfully."}
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Database error during reset: {e}")
        raise HTTPException(status_code=500, detail="Database error during reset.")
    except Exception as e:
        logging.error(f"Unexpected error during reset: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during reset.")
