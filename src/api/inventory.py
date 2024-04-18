from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
from pydantic import BaseModel
from typing import Optional

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

class CapacityPurchase(BaseModel):
    red_potion_capacity: Optional[int] = None
    green_potion_capacity: Optional[int] = None
    blue_potion_capacity: Optional[int] = None
    ml_capacity: Optional[int] = None

@router.get("/audit")
def get_inventory_audit():
    with db.engine.begin() as connection:
        inventory_query = sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions,  num_green_ml, num_red_ml, num_blue_ml, gold FROM global_inventory"
        )
        inventory_result = connection.execute(inventory_query).first()
        if not inventory_result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        capacity_query = sqlalchemy.text(
            "SELECT red_potion_capacity, green_potion_capacity, blue_potion_capacity, ml_capacity FROM capacity_inventory"
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
            "red_potion_capacity": capacity_result.red_potion_capacity,
            "green_potion_capacity": capacity_result.green_potion_capacity,
            "blue_potion_capacity": capacity_result.blue_potion_capacity,
            "ml_capacity": capacity_result.ml_capacity
        }

@router.post("/plan")
def update_inventory_capacity(capacity_purchase: CapacityPurchase):
    # Validate that provided values are positive, if present
    if any(
        value is not None and value < 0
        for value in capacity_purchase.dict().values()
    ):
        raise HTTPException(status_code=400, detail="Capacity values must be positive if provided.")

    with db.engine.begin() as connection:
        # Fetch the current capacity to use as default values
        current_capacity = connection.execute(
            sqlalchemy.text(
                "SELECT red_potion_capacity, green_potion_capacity, blue_potion_capacity, ml_capacity "
                "FROM capacity_inventory WHERE id = 1"
            )
        ).first()

        # Create a dictionary of current capacity
        capacity_defaults = {
            "red_potion_capacity": current_capacity.red_potion_capacity,
            "green_potion_capacity": current_capacity.green_potion_capacity,
            "blue_potion_capacity": current_capacity.blue_potion_capacity,
            "ml_capacity": current_capacity.ml_capacity
        }

        # Overwrite defaults with any provided values
        update_values = {
            key: value if value is not None else capacity_defaults[key]
            for key, value in capacity_purchase.dict().items()
        }

        # Build the update query using new values
        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET red_potion_capacity = :red_potion_capacity,
                green_potion_capacity = :green_potion_capacity,
                blue_potion_capacity = :blue_potion_capacity,
                ml_capacity = :ml_capacity
            WHERE id = 1
        """)

        # Execute the update query
        connection.execute(update_query, update_values)

        return {"status": "Inventory capacity updated successfully."}

@router.post("/deliver/{order_id}")
def deliver_capacity_plan(order_id: int, capacity_purchase: CapacityPurchase):
    with db.engine.begin() as connection:
        # Fetch the current capacity to use as default values
        current_capacity = connection.execute(
            sqlalchemy.text(
                "SELECT red_potion_capacity, green_potion_capacity, blue_potion_capacity, ml_capacity, gold "
                "FROM capacity_inventory JOIN global_inventory ON capacity_inventory.id = global_inventory.id "
                "WHERE capacity_inventory.id = 1"
            )
        ).first()

        # Set the default cost multiplier
        cost_multiplier = 1000  # Example cost calculation

        # Calculate the total cost using either the provided values or the default ones
        total_cost = sum(
            (getattr(capacity_purchase, key) if getattr(capacity_purchase, key) is not None else getattr(current_capacity, key))
            * cost_multiplier for key in ['red_potion_capacity', 'green_potion_capacity', 'blue_potion_capacity', 'ml_capacity']
        )

        if current_capacity.gold < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient gold for capacity expansion.")

        # Deduct the total cost from the gold
        connection.execute(
            sqlalchemy.text("UPDATE global_inventory SET gold = gold - :cost"),
            {'cost': total_cost}
        )
        
        # Prepare the new values for updating capacity, defaulting to the current capacity if not provided
        update_values = {
            key: getattr(capacity_purchase, key) if getattr(capacity_purchase, key) is not None else getattr(current_capacity, key)
            for key in ['red_potion_capacity', 'green_potion_capacity', 'blue_potion_capacity', 'ml_capacity']
        }

        # Update the capacity
        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET red_potion_capacity = red_potion_capacity + :red_potion_capacity,
                green_potion_capacity = green_potion_capacity + :green_potion_capacity,
                blue_potion_capacity = blue_potion_capacity + :blue_potion_capacity,
                ml_capacity = ml_capacity + :ml_capacity
            WHERE id = 1
        """)
        connection.execute(update_query, update_values)

        return {"status": f"Capacity delivered and updated successfully for order_id {order_id}."}
