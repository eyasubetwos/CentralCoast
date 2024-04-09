import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

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
    """
    Update the inventory with delivered potions.
    """
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            if potion.potion_type == [0, 100, 0, 0]:  # Assuming this represents green potions
                # Fetch current inventory of green potions
                inventory_query = "SELECT num_green_potions FROM global_inventory"
                inventory_result = connection.execute(sqlalchemy.text(inventory_query)).first()
                num_green_potions = inventory_result[0] if inventory_result else 0
                
                # Update inventory with delivered potions
                new_num_green_potions = num_green_potions + potion.quantity
                update_query = "UPDATE global_inventory SET num_green_potions = :new_num WHERE potion_type = 'green'"
                connection.execute(sqlalchemy.text(update_query), new_num=new_num_green_potions)

    return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}


@router.post("/plan")
def get_bottle_plan():
    """
    Generate a plan to bottle potions from barrels, focusing on utilizing available liquid volumes.
    """
    with db.engine.begin() as connection:
        # Fetch current volumes of liquid for potions
        liquid_query = "SELECT num_green_ml FROM global_inventory"
        liquid_result = connection.execute(sqlalchemy.text(liquid_query)).first()
        num_green_ml = liquid_result[0] if liquid_result else 0

        # Assume each potion requires 100 ml to bottle
        potion_requirement_ml = 100
        max_potions = num_green_ml // potion_requirement_ml

        if max_potions > 0:
            # Update inventory to reflect the planned bottling
            new_num_green_ml = num_green_ml - (max_potions * potion_requirement_ml)
            update_liquid_query = "UPDATE global_inventory SET num_green_ml = :new_ml WHERE potion_type = 'green'"
            connection.execute(sqlalchemy.text(update_liquid_query), new_ml=new_num_green_ml)

            return [{"potion_type": [0, 100, 0, 0], "quantity": max_potions}]
        else:
            raise HTTPException(status_code=400, detail="Insufficient liquid for bottling any potions.")

if __name__ == "__main__":
    print(get_bottle_plan())
