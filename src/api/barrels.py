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
    sku: str
    ml_per_barrel: int
    potion_type: list[int]  # Expects a list with 4 integers representing the potion color mix
    price: int
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    with db.engine.begin() as connection:
        # Aggregate total cost and update ml for each potion color
        total_cost = 0
        ml_update = {'red': 0, 'green': 0, 'blue': 0}
        
        # Calculate total cost and ml to be updated
        for barrel in barrels_delivered:
            total_cost += barrel.price * barrel.quantity
            potion_color_mix = barrel.potion_type  # Assuming [red%, green%, blue%, _]
            ml_update['red'] += potion_color_mix[0] / 100 * barrel.ml_per_barrel * barrel.quantity
            ml_update['green'] += potion_color_mix[1] / 100 * barrel.ml_per_barrel * barrel.quantity
            ml_update['blue'] += potion_color_mix[2] / 100 * barrel.ml_per_barrel * barrel.quantity

        # Check gold availability
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        if current_gold < total_cost:
            raise HTTPException(status_code=400, detail="Not enough gold for barrel purchase.")

        # Update the inventory with new ml and deduct cost
        update_query = sqlalchemy.text("""
            UPDATE global_inventory
            SET num_red_ml = num_red_ml + :red_ml,
                num_green_ml = num_green_ml + :green_ml,
                num_blue_ml = num_blue_ml + :blue_ml,
                gold = gold - :total_cost
        """)
        connection.execute(update_query, red_ml=ml_update['red'], green_ml=ml_update['green'], blue_ml=ml_update['blue'], total_cost=total_cost)

        return {"status": "Barrels delivered and inventory updated for order_id " + str(order_id)}

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    with db.engine.begin() as connection:
        # Get the current ml for each potion color from the inventory
        inventory_query = sqlalchemy.text("""
            SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory
        """)
        current_ml = connection.execute(inventory_query).first()
        num_red_ml, num_green_ml, num_blue_ml = current_ml if current_ml else (0, 0, 0)

    purchase_plan = []
    # Thresholds for each potion color in ml
    potion_thresholds = {'red': 500, 'green': 500, 'blue': 500}

    # Check if any potion color is below its threshold and needs replenishing
    for barrel in wholesale_catalog:
        if barrel.potion_type[0] > 0 and num_red_ml < potion_thresholds['red']:
            purchase_plan.append({"sku": barrel.sku, "quantity": 1})
            potion_thresholds['red'] -= barrel.ml_per_barrel  # Adjust threshold
        elif barrel.potion_type[1] > 0 and num_green_ml < potion_thresholds['green']:
            purchase_plan.append({"sku": barrel.sku, "quantity": 1})
            potion_thresholds['green'] -= barrel.ml_per_barrel  # Adjust threshold
        elif barrel.potion_type[2] > 0 and num_blue_ml < potion_thresholds['blue']:
            purchase_plan.append({"sku": barrel.sku, "quantity": 1})
            potion_thresholds['blue'] -= barrel.ml_per_barrel  # Adjust threshold

        # If all thresholds are met or exceeded, stop purchasing
        if all(ml >= 0 for ml in potion_thresholds.values()):
            break

    return purchase_plan