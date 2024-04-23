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
    try:
        with db.engine.begin() as connection:
            # Process each potion delivery within a transaction
            for potion in potions_delivered:
                # Get the SKU of the potion based on its composition
                sku = f"{potion.red_potion}_{potion.green_potion}_{potion.blue_potion}"
                potion_mix = db.find_one_potion_mix(sku)
                if potion_mix:
                    # Update the inventory_quantity for the potion mix
                    db.update_potion_mix(sku, {'inventory_quantity': sqlalchemy.literal_column('inventory_quantity') + 1})
                else:
                    raise HTTPException(status_code=404, detail=f"Potion mix with SKU {sku} not found.")

        return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan")
def get_bottle_plan():
    try:
        with db.engine.begin() as connection:
            # Get all potion mixes from the database
            potion_mixes = db.find_all_potion_mixes()

            bottling_plan = []
            for mix in potion_mixes:
                # Calculate the quantity of each potion type based on the inventory and maximum capacity
                max_potions = min(mix.red_percentage, mix.green_percentage, mix.blue_percentage) * mix.inventory_quantity // 100
                if max_potions > 0:
                    # Append the bottling plan for each potion type
                    bottling_plan.append({"potion_type": [mix.red_percentage, mix.green_percentage, mix.blue_percentage, mix.dark_percentage], "quantity": max_potions})

            return bottling_plan

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(get_bottle_plan())
