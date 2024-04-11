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
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            if barrel.potion_type == [0, 100, 0, 0]:  # Assuming [0, 100, 0, 0] indicates green potion
                update_query = sqlalchemy.text("""
                    UPDATE global_inventory
                    SET num_green_ml = num_green_ml + :added_ml,
                        gold = gold - :spent_gold
                    WHERE id = 1  # Assuming there's only one row and its ID is 1
                """)
                connection.execute(update_query, added_ml=(barrel.ml_per_barrel * barrel.quantity), spent_gold=(barrel.price * barrel.quantity))

    return {"status": "Barrels delivered and inventory updated."}

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    with db.engine.begin() as connection:
        inventory_query = "SELECT num_green_potions FROM global_inventory"
        result = connection.execute(sqlalchemy.text(inventory_query))
        num_green_potions = result.scalar() if result else 0

    purchase_plan = []
    potion_threshold = 10  # Threshold to determine when to purchase more
    if num_green_potions < potion_threshold:
        for barrel in wholesale_catalog:
            if barrel.potion_type == [0, 100, 0, 0]:  # Assuming this represents green potion
                purchase_plan.append({"sku": barrel.sku, "quantity": 1})
                break  # Only purchase one barrel for simplicity

    return purchase_plan