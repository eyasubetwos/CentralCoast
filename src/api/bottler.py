import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    red_potion: int = 0
    green_potion: int = 0
    blue_potion: int = 0

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    with db.engine.begin() as connection:
        # Update the inventory for each potion type delivered
        for potion in potions_delivered:
            update_query = sqlalchemy.text("""
                UPDATE global_inventory
                SET num_red_potions = num_red_potions + :red,
                    num_green_potions = num_green_potions + :green,
                    num_blue_potions = num_blue_potions + :blue
                WHERE id = 1  # Assuming single inventory row with ID 1
            """)
            connection.execute(update_query, red=potion.red_potion, green=potion.green_potion, blue=potion.blue_potion)

    return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        liquid_query = sqlalchemy.text("""
            SELECT num_red_ml, num_green_ml, num_blue_ml
            FROM global_inventory
            WHERE id = 1
        """)
        liquid_result = connection.execute(liquid_query).first()

        if not liquid_result:
            raise HTTPException(status_code=404, detail="Liquid inventory not found.")

        # Calculate the number of potions that can be made for each type
        max_red_potions = liquid_result.num_red_ml // 100
        max_green_potions = liquid_result.num_green_ml // 100
        max_blue_potions = liquid_result.num_blue_ml // 100

        # Update liquid quantities in inventory
        new_num_red_ml = liquid_result.num_red_ml - (max_red_potions * 100)
        new_num_green_ml = liquid_result.num_green_ml - (max_green_potions * 100)
        new_num_blue_ml = liquid_result.num_blue_ml - (max_blue_potions * 100)

        update_liquid_query = sqlalchemy.text("""
            UPDATE global_inventory 
            SET num_red_ml = :new_red_ml,
                num_green_ml = :new_green_ml,
                num_blue_ml = :new_blue_ml
            WHERE id = 1
        """)
        connection.execute(update_liquid_query, 
                           new_red_ml=new_num_red_ml, 
                           new_green_ml=new_num_green_ml,
                           new_blue_ml=new_num_blue_ml)

        # Formulate the bottling plan
        bottling_plan = []
        if max_red_potions > 0:
            bottling_plan.append({"potion_type": [100, 0, 0, 0], "quantity": max_red_potions})
        if max_green_potions > 0:
            bottling_plan.append({"potion_type": [0, 100, 0, 0], "quantity": max_green_potions})
        if max_blue_potions > 0:
            bottling_plan.append({"potion_type": [0, 0, 100, 0], "quantity": max_blue_potions})

        return bottling_plan

if name == "main":
    print(get_bottle_plan())