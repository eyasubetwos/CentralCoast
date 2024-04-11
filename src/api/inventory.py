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
def get_inventory_audit():
    with db.engine.begin() as connection:
        inventory_query = sqlalchemy.text("SELECT num_green_potions, num_green_ml, gold FROM global_inventory")
        inventory_result = connection.execute(inventory_query).first()
        if not inventory_result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        capacity_query = sqlalchemy.text("SELECT potion_capacity, ml_capacity FROM capacity_inventory")
        capacity_result = connection.execute(capacity_query).first()
        if not capacity_result:
            raise HTTPException(status_code=404, detail="Capacity data not found.")

        return {
            "number_of_potions": inventory_result[0],
            "ml_in_barrels": inventory_result[1],
            "gold": inventory_result[2],
            "potion_capacity": capacity_result[0],
            "ml_capacity": capacity_result[1]
        }

@router.post("/plan")
def update_inventory_capacity(capacity_purchase: CapacityPurchase):
    with db.engine.begin() as connection:
        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET potion_capacity = potion_capacity + :potion_capacity,
                ml_capacity = ml_capacity + :ml_capacity
        """)
        connection.execute(update_query, potion_capacity=capacity_purchase.potion_capacity, ml_capacity=capacity_purchase.ml_capacity)

        return {"status": "Inventory capacity updated successfully."}

@router.post("/deliver/{order_id}")
def deliver_capacity_plan(order_id: int, capacity_purchase: CapacityPurchase):
    with db.engine.begin() as connection:
        # Calculate cost based on a fixed price per unit increase, e.g., 1000 gold per unit
        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        gold_query = sqlalchemy.text("SELECT gold FROM global_inventory")
        gold = connection.execute(gold_query).scalar()

        if gold < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient gold for capacity expansion.")

        connection.execute(sqlalchemy.text("""
            UPDATE global_inventory SET gold = gold - :cost
        """), cost=total_cost)

        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET potion_capacity = potion_capacity + :potion_capacity,
                ml_capacity = ml_capacity + :ml_capacity
        """)
        connection.execute(update_query, potion_capacity=capacity_purchase.potion_capacity, ml_capacity=capacity_purchase.ml_capacity)

        return {"status": f"Capacity delivered and updated successfully for order_id {order_id}."}
