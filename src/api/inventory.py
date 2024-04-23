from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
import logging
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

@router.get("/audit")
def get_inventory():
    try:
        with db.engine.begin() as connection:
            # Log the attempt to retrieve inventory data
            logging.info("Retrieving inventory data from global_inventory.")
            inventory_query = sqlalchemy.text("SELECT * FROM global_inventory")
            inventory_result = connection.execute(inventory_query).first()
            if not inventory_result:
                logging.error("No inventory data found in global_inventory.")
                raise HTTPException(status_code=404, detail="Inventory data not found.")

            inventory_data = {key: value for key, value in inventory_result.items()}

            logging.info("Retrieving capacity data from capacity_inventory.")
            capacity_query = sqlalchemy.text("SELECT * FROM capacity_inventory")
            capacity_result = connection.execute(capacity_query).first()
            if not capacity_result:
                logging.error("No capacity data found in capacity_inventory.")
                raise HTTPException(status_code=404, detail="Capacity data not found.")

            for key, value in capacity_result.items():
                inventory_data[key] = value

            logging.info("Fetching all available potion mixes from potion_mixes.")
            potion_mixes_query = sqlalchemy.text("SELECT * FROM potion_mixes")
            potion_mixes_result = connection.execute(potion_mixes_query).fetchall()

            for potion_mix in potion_mixes_result:
                inventory_data[potion_mix['sku']] = {
                    "name": potion_mix['name'],
                    "quantity": potion_mix['inventory_quantity'],
                    "price": potion_mix['price'],
                    "potion_composition": potion_mix['potion_composition']
                }

            return inventory_data
    except SQLAlchemyError as e:
        logging.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/plan")
def get_capacity_plan():
    """
    Calculate how much additional potion and ml capacity can be bought with available gold.
    Each unit costs 1000 gold. Assumes no partial purchases are allowed.
    """
    with db.engine.begin() as connection:
        gold_query = sqlalchemy.text("SELECT gold FROM global_inventory WHERE id = 1")
        current_gold = connection.execute(gold_query).scalar()
        cost_query = sqlalchemy.text("SELECT gold_cost_per_unit FROM capacity_inventory WHERE id = 1")
        cost_per_unit = connection.execute(cost_query).scalar()

        if current_gold is None or cost_per_unit is None:
            raise HTTPException(status_code=404, detail="Required inventory data not found.")

        additional_units = current_gold // cost_per_unit
        additional_potion_capacity = additional_units * 50
        additional_ml_capacity = additional_units * 10000 

        return {
            "current_gold": current_gold,
            "cost_per_unit": cost_per_unit,
            "additional_potion_capacity": additional_potion_capacity,
            "additional_ml_capacity": additional_ml_capacity
        }


@router.post("/deliver/{order_id}")
def deliver_capacity_plan(order_id: int):
    """
    Automatically purchase additional capacity for potions and ml based on available gold.
    Each unit costs 1000 gold and provides 50 potion slots and 10000 ml.
    """
    with db.engine.begin() as connection:
        # Fetch the current amount of gold from the global_inventory table
        gold_query = sqlalchemy.text("SELECT gold FROM global_inventory WHERE id = 1")
        current_gold = connection.execute(gold_query).scalar()
        
        # Fetch the cost per unit of capacity from the capacity_inventory table
        cost_query = sqlalchemy.text("SELECT gold_cost_per_unit FROM capacity_inventory WHERE id = 1")
        cost_per_unit = connection.execute(cost_query).scalar()

        if current_gold is None or cost_per_unit is None:
            raise HTTPException(status_code=404, detail="Required inventory data not found.")

        # Calculate how many additional units of capacity can be bought
        additional_units = current_gold // cost_per_unit

        # Update the shop's capacity based on the additional units that can be afforded
        connection.execute(sqlalchemy.text("""
            UPDATE capacity_inventory SET
            potion_capacity = potion_capacity + :additional_units * 50,
            ml_capacity = ml_capacity + :additional_units * 10000
            WHERE id = 1
        """), {'additional_units': additional_units})

        # Deduct the cost of the capacity from the gold
        connection.execute(sqlalchemy.text("""
            UPDATE global_inventory SET gold = gold - :cost
            WHERE id = 1
        """), {'cost': additional_units * cost_per_unit})

        return {"status": "OK", "message": f"Capacity purchased and inventory updated for order_id {order_id}"}
