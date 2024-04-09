from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """
    Processes delivered barrels by updating the global inventory.
    """
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            if barrel.potion_type == [0, 100, 0, 0]:  
                inventory_query = "SELECT num_green_ml, gold FROM global_inventory"
                inventory_result = connection.execute(sqlalchemy.text(inventory_query)).first()
                num_green_ml, gold = inventory_result if inventory_result else (0, 100)
                new_ml = num_green_ml + (barrel.ml_per_barrel * barrel.quantity)
                new_gold = gold - (barrel.price * barrel.quantity)
                update_query = "UPDATE global_inventory SET num_green_ml = :new_ml, gold = :new_gold"
                connection.execute(sqlalchemy.text(update_query), new_ml=new_ml, new_gold=new_gold)

    return {"status": "Barrels delivered and inventory updated."}

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    potion_threshold = 10 
    with db.engine.begin() as connection:
        inventory_query = "SELECT num_green_potions FROM global_inventory"
        inventory_result = connection.execute(sqlalchemy.text(inventory_query)).first()
        num_green_potions = inventory_result[0] if inventory_result else 0

    purchase_plan = []
    if num_green_potions < potion_threshold:
        for barrel in wholesale_catalog:
            if barrel.potion_type == [0, 100, 0, 0]:  
                purchase_plan.append({"sku": barrel.sku, "quantity": 1})
                break  
    return purchase_plan
