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
    red_potion_capacity: int
    green_potion_capacity: int
    blue_potion_capacity: int
    ml_capacity: int

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
    if any([
        capacity_purchase.red_potion_capacity < 0, 
        capacity_purchase.green_potion_capacity < 0,
        capacity_purchase.blue_potion_capacity < 0,
        capacity_purchase.ml_capacity < 0
    ]):
        raise HTTPException(status_code=400, detail="Capacity values must be positive.")

    with db.engine.begin() as connection:
        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET red_potion_capacity = red_potion_capacity + :red_potion_capacity,
                green_potion_capacity = green_potion_capacity + :green_potion_capacity,
                blue_potion_capacity = blue_potion_capacity + :blue_potion_capacity,
                ml_capacity = ml_capacity + :ml_capacity
        """)
        connection.execute(update_query, capacity_purchase.dict())

        return {"status": "Inventory capacity updated successfully."}

@router.post("/deliver/{order_id}")
def deliver_capacity_plan(order_id: int, capacity_purchase: CapacityPurchase):
    with db.engine.begin() as connection:
        total_cost = (capacity_purchase.red_potion_capacity + 
                      capacity_purchase.green_potion_capacity + 
                      capacity_purchase.blue_potion_capacity +
                      capacity_purchase.ml_capacity) * 1000  # Example cost calculation
        gold_query = sqlalchemy.text("SELECT gold FROM global_inventory")
        gold = connection.execute(gold_query).scalar()

        if gold < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient gold for capacity expansion.")

        connection.execute(sqlalchemy.text("""
            UPDATE global_inventory SET gold = gold - :cost
        """), {cost=total_cost})
        
        update_query = sqlalchemy.text("""
            UPDATE capacity_inventory
            SET red_potion_capacity = red_potion_capacity + :red_potion_capacity,
                green_potion_capacity = green_potion_capacity + :green_potion_capacity,
                blue_potion_capacity = blue_potion_capacity + :blue_potion_capacity,
                ml_capacity = ml_capacity + :ml_capacity
        """)
        connection.execute(update_query, capacity_purchase.dict())

        return {"status": f"Capacity delivered and updated successfully for order_id {order_id}."}