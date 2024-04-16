from fastapi import APIRouter, Depends, HTTPException
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
    sku: str  # This should match specific potion types e.g., 'RED_POTION', 'GREEN_POTION', 'BLUE_POTION'
    ml_per_barrel: int
    price: int
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    with db.engine.begin() as connection:
        total_cost = sum(barrel.price * barrel.quantity for barrel in barrels_delivered)
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        if current_gold < total_cost:
            raise HTTPException(status_code=400, detail="Not enough gold to complete the transaction.")

        for barrel in barrels_delivered:
            potion_type_field = f'num_{barrel.sku.lower()}_ml'  # Constructs field name dynamically based on SKU
            update_ml = barrel.ml_per_barrel * barrel.quantity
            update_query = sqlalchemy.text(f"""
                UPDATE global_inventory
                SET {potion_type_field} = {potion_type_field} + :update_ml,
                    gold = gold - :spent_gold
            """)
            connection.execute(update_query, update_ml=update_ml, spent_gold=barrel.price * barrel.quantity)

        return {"status": f"Barrels delivered and inventory updated for order_id {order_id}"}

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    with db.engine.begin() as connection:
        # Get the current ml for each potion type from the inventory
        inventory_query = sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory")
        current_ml = connection.execute(inventory_query).first()

    if not current_ml:
        raise HTTPException(status_code=404, detail="Inventory data not found.")

    num_red_ml, num_green_ml, num_blue_ml = current_ml
    purchase_plan = []

    # Define the purchase thresholds for each potion type
    thresholds = {
        'RED_POTION': 500,
        'GREEN_POTION': 500,
        'BLUE_POTION': 500
    }

    # Determine purchase needs based on current inventory and thresholds
    for barrel in wholesale_catalog:
        potion_type = barrel.sku.upper()  # SKU must correspond to potion types like 'RED_POTION'
        if potion_type not in thresholds:
            continue  # Skip if the barrel's SKU does not correspond to a known potion type

        potion_ml_field = f'num_{potion_type.lower()}_ml'
        current_potion_ml = getattr(current_ml, potion_ml_field, 0)  # Get the current ml for the potion type dynamically

        # Check if additional ml is needed for this potion type
        if current_potion_ml < thresholds[potion_type]:
            purchase_plan.append({"sku": barrel.sku, "quantity": 1})
            # Assume each barrel replenishes a standard quantity, e.g., one barrel per purchase until threshold is met
            break  # Optional: Remove break if multiple barrels should be purchased at once

    return purchase_plan