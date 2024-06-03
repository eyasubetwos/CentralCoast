from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
import logging
import datetime

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potion inventories are ledger-reset,
    and all barrels and carts are reset. The potion mixes are reset to their initial state
    as defined in the potion_mixes table.
    """
    try:
        with db.engine.begin() as connection:
            # Clearing all ledger entries
            logging.info("Clearing inventory ledger...")
            connection.execute(sqlalchemy.text("DELETE FROM inventory_ledger"))

            # Resetting global inventory via ledger
            logging.info("Resetting global inventory via ledger...")
            connection.execute(sqlalchemy.text("""
                INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                VALUES 
                    ('gold', 'N/A', 100, 'Reset gold to initial state', :date),
                    ('potion', 'GP-001', 0, 'Initial green potion stock', :date),
                    ('potion', 'RP-001', 0, 'Initial red potion stock', :date),
                    ('potion', 'BP-001', 0, 'Initial blue potion stock', :date),
                    ('ml', 'green', 5000, 'Initial green ml stock', :date),
                    ('ml', 'red', 5000, 'Initial red ml stock', :date),
                    ('ml', 'blue', 5000, 'Initial blue ml stock', :date)
            """), {'date': datetime.datetime.now()})

            # Clearing and resetting potion mixes
            logging.info("Clearing potion mixes...")
            connection.execute(sqlalchemy.text("DELETE FROM potion_mixes"))

            logging.info("Reinserting initial potion mixes...")
            initial_potion_mixes = [
                {"name": 'Green Potion', "potion_composition": '{"green": 100, "red": 0, "blue": 0, "dark": 0}', "sku": 'GP-001', "price": 25.00, "inventory_quantity": 0},
                {"name": 'Red Potion', "potion_composition": '{"red": 100, "blue": 0, "dark": 0, "green": 0}', "sku": 'RP-001', "price": 25.00, "inventory_quantity": 0},
                {"name": 'Blue Potion', "potion_composition": '{"blue": 100, "red": 0, "dark": 0, "green": 0}', "sku": 'BP-001', "price": 25.00, "inventory_quantity": 0},
                {"name": 'Purple Potion', "potion_composition": '{"green": 50, "red": 0, "blue": 50, "dark": 0}', "sku": 'PP-001', "price": 25.00, "inventory_quantity": 0}
            ]
            for potion in initial_potion_mixes:
                connection.execute(sqlalchemy.text("""
                    INSERT INTO potion_mixes (name, potion_composition, sku, price, inventory_quantity)
                    VALUES (:name, :potion_composition, :sku, :price, :inventory_quantity)
                """), potion)

            # Clearing any customer visit logs and carts
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
