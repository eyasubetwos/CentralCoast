from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
from pydantic import BaseModel

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
    with db.engine.begin() as connection:
        # Retrieve inventory data for all potion types from the global_inventory table
        inventory_query = sqlalchemy.text(
            "SELECT * FROM global_inventory"
        )
        inventory_result = connection.execute(inventory_query).first()
        if not inventory_result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        # Retrieve capacity data from the capacity_inventory table
        capacity_query = sqlalchemy.text(
            "SELECT * FROM capacity_inventory"
        )
        capacity_result = connection.execute(capacity_query).first()
        if not capacity_result:
            raise HTTPException(status_code=404, detail="Capacity data not found.")

        # Fetch all available potion mixes from the potion_mixes table
        potion_mixes_query = sqlalchemy.text(
            "SELECT * FROM potion_mixes"
        )
        potion_mixes_result = connection.execute(potion_mixes_query).fetchall()

        # Construct inventory dictionary dynamically based on potion mixes
        inventory_data = dict(inventory_result)
        for potion_mix in potion_mixes_result:
            inventory_data[potion_mix.sku] = {
                "name": potion_mix.name,
                "quantity": potion_mix.inventory_quantity,
                "price": potion_mix.price,
                "potion_composition": potion_mix.potion_composition
            }

        return inventory_data

@router.post("/plan")
def get_capacity_plan():
    """
    Calculate how much additional potion and ml capacity can be bought with available gold.
    Each unit costs 1000 gold. Assumes no partial purchases are allowed.
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

        additional_potion_capacity = additional_units * 50
        additional_ml_capacity = additional_units * 10000 

        return {
            "additional_potion_capacity": additional_potion_capacity,
            "additional_ml_capacity": additional_ml_capacity
        }


@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """
    Purchase additional capacity for potions and ml based on the capacity units specified in the request body.
    """
    # Assume 1 unit of potion capacity is equivalent to 50 potions, and each potion can hold 200 ml
    # Thus, 1 unit of ml capacity is 50 * 200 = 10000 ml
    potion_capacity_increase = capacity_purchase.potion_capacity
    ml_capacity_increase = capacity_purchase.ml_capacity  # Each potion holds 200 ml
    cost_per_unit = 1000  # Assume each unit costs 1000 gold

    total_cost = cost_per_unit * (capacity_purchase.ml_capacity / 10000)

    with db.engine.begin() as connection:
        # Check if there's enough gold for the purchase
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory WHERE id = 1")).scalar()
        if current_gold < total_cost:
            raise HTTPException(status_code=400, detail="Not enough gold to purchase additional capacity.")

        # Deduct the cost of the capacity from the gold
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = gold - :cost WHERE id = 1"), {'cost': total_cost})

        # Update the capacity inventory with the new capacities
        connection.execute(sqlalchemy.text("""
            UPDATE capacity_inventory SET
            potion_capacity = potion_capacity + :potion_capacity,
            ml_capacity = ml_capacity + :ml_capacity
            WHERE id = 1
        """), {'potion_capacity': potion_capacity_increase, 'ml_capacity': ml_capacity_increase})

        return {"status": "OK", "message": f"Capacity purchased and inventory updated for order_id {order_id}"}
