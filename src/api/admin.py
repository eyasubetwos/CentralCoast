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
            logging.info("Resetting global inventory gold...")
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = 100"))

            logging.info("Clearing potion mixes...")
            connection.execute(sqlalchemy.text("DELETE FROM potion_mixes"))

            logging.info("Reinserting initial potion mixes...")
            initial_potion_mixes = [
                {"name": row.name, "potion_composition": row.potion_composition, "sku": row.sku, "price": row.price, "inventory_quantity": row.inventory_quantity}
                for row in connection.execute(sqlalchemy.text("SELECT name, potion_composition, sku, price, inventory_quantity FROM potion_mixes"))
            ]
            for potion in initial_potion_mixes:
                connection.execute(sqlalchemy.text("""
                    INSERT INTO potion_mixes (name, potion_composition, sku, price, inventory_quantity)
                    VALUES (:name, :potion_composition, :sku, :price, :inventory_quantity)
                """), potion)

            logging.info("Resetting capacity inventory...")
            connection.execute(sqlalchemy.text("UPDATE capacity_inventory SET potion_capacity = 50, ml_capacity = 10000 WHERE id = 1"))

            logging.info("Clearing customer visits and carts...")
            connection.execute(sqlalchemy.text("DELETE FROM customer_visits"))
            connection.execute(sqlalchemy.text("DELETE FROM carts"))
            connection.execute(sqlalchemy.text("DELETE FROM cart_items"))

            logging.info("Game state has been reset successfully.")
        return {"status": "Game state reset successfully."}
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Database error during reset: {e}")
        raise HTTPException(status_code=500, detail=f"Database error during reset: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during reset: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during reset: {e}")
