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
        # Process each potion delivery within a transaction
        for potion in potions_delivered:
            update_query = sqlalchemy.text("""
                UPDATE global_inventory
                SET num_red_potions = num_red_potions + :red,
                    num_green_potions = num_green_potions + :green,
                    num_blue_potions = num_blue_potions + :blue
                WHERE id = 1
            """)
            connection.execute(
                update_query, 
                {
                    'red': potion.red_potion, 
                    'green': potion.green_potion, 
                    'blue': potion.blue_potion
                }
            )

    return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        # Begin transaction to ensure inventory integrity
        transaction = connection.begin()
        try:
            liquid_query = sqlalchemy.text("""
                SELECT num_red_ml, num_green_ml, num_blue_ml
                FROM global_inventory
                WHERE id = 1
            """)
            liquid_result = connection.execute(liquid_query).first()

            if not liquid_result:
                raise HTTPException(status_code=404, detail="Liquid inventory not found.")

            max_red_potions = liquid_result.num_red_ml // 100
            max_green_potions = liquid_result.num_green_ml // 100
            max_blue_potions = liquid_result.num_blue_ml // 100

            update_liquid_query = sqlalchemy.text("""
                UPDATE global_inventory 
                SET num_red_ml = num_red_ml - :red_ml_used,
                    num_green_ml = num_green_ml - :green_ml_used,
                    num_blue_ml = num_blue_ml - :blue_ml_used
                WHERE id = 1
            """)

            connection.execute(
                               update_liquid_query, 
                               {
                                  'red_ml_used': max_red_potions * 100, 
                                  'green_ml_used': max_green_potions * 100,
                                  'blue_ml_used': max_blue_potions * 100
                               }
                              )

            transaction.commit()  # Commit changes to ensure data consistency

            bottling_plan = []
            if max_red_potions > 0:
                bottling_plan.append({"potion_type": [100, 0, 0, 0], "quantity": max_red_potions})
            if max_green_potions > 0:
                bottling_plan.append({"potion_type": [0, 100, 0, 0], "quantity": max_green_potions})
            if max_blue_potions > 0:
                bottling_plan.append({"potion_type": [0, 0, 100, 0], "quantity": max_blue_potions})

            return bottling_plan
        except Exception as e:
            transaction.rollback()  # Roll back on any error
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(get_bottle_plan())