from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from fastapi import HTTPException
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    with db.engine.begin() as connection:
        inventory_result = connection.execute(sqlalchemy.text(
            "SELECT num_green_potions, num_green_ml, gold FROM global_inventory"
        )).first()
        capacity_result = connection.execute(sqlalchemy.text(
            "SELECT potion_capacity, ml_capacity FROM capacity_inventory"
        )).first()

        if inventory_result and capacity_result:
            return {
                "number_of_potions": inventory_result.num_green_potions,
                "ml_in_barrels": inventory_result.num_green_ml,
                "gold": inventory_result.gold,
                "potion_capacity": capacity_result.potion_capacity,
                "ml_capacity": capacity_result.ml_capacity
            }
        else:
            raise HTTPException(status_code=404, detail="Inventory record not found.")

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    with db.engine.begin() as connection:
        capacity_result = connection.execute(sqlalchemy.text(
            "SELECT potion_capacity, ml_capacity FROM capacity_inventory"
        )).first()
        if capacity_result:
            return {
                "potion_capacity": capacity_result.potion_capacity,
                "ml_capacity": capacity_result.ml_capacity
            }
        else:
            return {
                "potion_capacity": 50, 
                "ml_capacity": 10000   
            }


class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text(
            "SELECT gold FROM global_inventory"
        )).scalar()

        cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        if cost > current_gold:
            raise HTTPException(status_code=400, detail="Insufficient gold to purchase capacity.")

        connection.execute(sqlalchemy.text(
            "UPDATE capacity_inventory SET "
            "potion_capacity = potion_capacity + :potion_capacity, "
            "ml_capacity = ml_capacity + :ml_capacity"
        ), potion_capacity=capacity_purchase.potion_capacity, 
           ml_capacity=capacity_purchase.ml_capacity)

        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET gold = gold - :cost"
        ), cost=cost)

    return {"status": "Capacity plan delivered successfully."}