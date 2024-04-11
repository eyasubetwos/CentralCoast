import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
from fastapi import HTTPException

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            if potion.potion_type == [0, 100, 0, 0]:  # Green potion type
                inventory_query = "SELECT num_green_potions FROM global_inventory"
                inventory_result = connection.execute(sqlalchemy.text(inventory_query)).first()
                if inventory_result:
                    new_num_green_potions = inventory_result[0] + potion.quantity
                    update_query = sqlalchemy.text("""
                        UPDATE global_inventory 
                        SET num_green_potions = :new_num
                    """)
                    connection.execute(update_query, new_num=new_num_green_potions)

    return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        liquid_query = "SELECT num_green_ml FROM global_inventory"
        liquid_result = connection.execute(sqlalchemy.text(liquid_query)).first()
        if liquid_result and liquid_result[0] >= 100:  # At least 100ml needed to bottle
            max_potions = liquid_result[0] // 100  # Determine how many potions can be made
            new_num_green_ml = liquid_result[0] - (max_potions * 100)
            update_liquid_query = sqlalchemy.text("""
                UPDATE global_inventory 
                SET num_green_ml = :new_ml
            """)
            connection.execute(update_liquid_query, new_ml=new_num_green_ml)
            return [{"potion_type": [0, 100, 0, 0], "quantity": max_potions}]
        else:
            raise HTTPException(status_code=400, detail="Insufficient liquid for bottling any potions.")

if __name__ == "__main__":
    print(get_bottle_plan())
