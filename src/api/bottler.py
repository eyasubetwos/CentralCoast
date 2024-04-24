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
    potion_composition: dict = {}

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    try:
        with db.engine.begin() as connection:
            for potion in potions_delivered:
                # Assuming potion_composition is a JSONB field in the database
                potion_mix = db.find_one_potion_mix(potion.potion_composition)
                if potion_mix:
                    db.update_potion_mix(potion_mix.sku, {'inventory_quantity': sqlalchemy.literal_column('inventory_quantity') + 1})
                else:
                    raise HTTPException(status_code=404, detail=f"Potion mix with composition {potion.potion_composition} not found.")

        return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan")
def get_bottle_plan():
    try:
        with db.engine.begin() as connection:
            # Fetch all potion mixes from the database
            potion_mixes = db.find_all_potion_mixes()

            bottling_plan = []
            for mix in potion_mixes:
                # Calculate the quantity of each potion type based on the inventory and maximum capacity
                max_potions = min(mix.potion_composition.values()) * mix.inventory_quantity // 100
                if max_potions > 0:
                    # Append the bottling plan for each potion type
                    bottling_plan.append({"potion_type": mix.potion_composition, "quantity": max_potions})

            return bottling_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))