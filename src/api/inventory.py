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
        inventory_query = sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions,  num_green_ml, num_red_ml, num_blue_ml, gold FROM global_inventory"
        )
        inventory_result = connection.execute(inventory_query).first()
        if not inventory_result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        capacity_query = sqlalchemy.text(
            "SELECT potion_capacity, ml_capacity FROM capacity_inventory"
        )
        capacity_result = connection.execute(capacity_query).first()
        if not capacity_result:
            raise HTTPException(status_code=404, detail="Capacity data not found.")

        return {
            "number_of_red_potions": inventory_result.num_red_potions,
            "number_of_green_potions": inventory_result.num_green_potions,
            "number_of_blue_potions": inventory_result.num_blue_potions,
            "ml_green_in_barrels": inventory_result.num_green_ml,
            "ml_red_in_barrels": inventory_result.num_red_ml,
            "ml_blue_in_barrels": inventory_result.num_blue_ml,
            "gold": inventory_result.gold,
            "potion_capacity": capacity_result.red_potion_capacity,
            "ml_capacity": capacity_result.ml_capacity
        }

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
    potion_capacity_increase = capacity_purchase.potion_capacity * 50
    ml_capacity_increase = capacity_purchase.ml_capacity * 200 * 50  # Each potion holds 200 ml
    cost_per_unit = 1000  # Assume each unit costs 1000 gold

    total_cost = cost_per_unit * (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity)

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
