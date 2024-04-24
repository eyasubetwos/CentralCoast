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
            logging.info("Clearing cart items...")
            connection.execute(sqlalchemy.text("DELETE FROM cart_items"))

            logging.info("Clearing carts...")
            connection.execute(sqlalchemy.text("DELETE FROM carts"))

            logging.info("Clearing customer visits...")
            connection.execute(sqlalchemy.text("DELETE FROM customer_visits"))

            logging.info("Resetting global inventory gold...")
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = 100"))

            logging.info("Clearing potion mixes...")
            connection.execute(sqlalchemy.text("DELETE FROM potion_mixes"))

            logging.info("Reinserting initial potion mixes...")
            initial_potion_mixes = [
                {"name": 'Green Potion', "potion_composition": '{"green": 100, "red": 0, "blue": 0, "dark": 0}', "sku": 'GP-001', "price": 50.00, "inventory_quantity": 50},
                {"name": 'Red Potion', "potion_composition": '{"red": 100, "blue": 0, "dark": 0, "green": 0}', "sku": 'RP-001', "price": 75.00, "inventory_quantity": 50},
                {"name": 'Blue Potion', "potion_composition": '{"blue": 100, "red": 0, "dark": 0, "green": 0}', "sku": 'BP-001', "price": 65.00, "inventory_quantity": 50},
                {"name": 'Purple Potion', "potion_composition": '{"green": 50, "red": 0, "blue": 50, "dark": 0}', "sku": 'PP-001', "price": 90.00, "inventory_quantity": 25}
            ]
            for potion in initial_potion_mixes:
                connection.execute(sqlalchemy.text("""
                    INSERT INTO potion_mixes (name, potion_composition, sku, price, inventory_quantity)
                    VALUES (:name, :potion_composition, :sku, :price, :inventory_quantity)
                """), potion)

            logging.info("Resetting capacity inventory...")
            connection.execute(sqlalchemy.text("UPDATE capacity_inventory SET potion_capacity = 50, ml_capacity = 10000 WHERE id = 1"))

            logging.info("Game state has been reset successfully.")
        return {"status": "Game state reset successfully."}
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Database error during reset: {e}")
        raise HTTPException(status_code=500, detail=f"Database error during reset: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during reset: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error during reset: {e}")
