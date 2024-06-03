from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api.barrels import post_deliver_barrels
import datetime

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    price: int
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    try:
        with db.engine.begin() as connection:
            total_cost = sum(barrel.price * barrel.quantity for barrel in barrels_delivered)
            current_gold_query = sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
            current_gold = connection.execute(current_gold_query).scalar() or 0

            if current_gold < total_cost:
                raise HTTPException(status_code=400, detail="Not enough gold to complete the transaction.")

            for barrel in barrels_delivered:
                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('ml', :sku, :change_amount, 'barrel delivery', :date)
                """), {'sku': barrel.sku, 'change_amount': barrel.ml_per_barrel * barrel.quantity, 'date': datetime.datetime.now()})

                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('gold', 'N/A', -:cost, 'barrel purchase', :date)
                """), {'cost': barrel.price * barrel.quantity, 'date': datetime.datetime.now()})

        return {"status": f"Barrels delivered and inventory updated for order_id {order_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def generate_order_id(connection):
    order_query = sqlalchemy.text("SELECT MAX(order_id) FROM orders")
    result = connection.execute(order_query).scalar()
    return (result or 0) + 1

def purchase_barrels_if_needed():
    try:
        with db.engine.begin() as connection:
            # Check current gold balance
            current_gold_query = sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
            current_gold = connection.execute(current_gold_query).scalar() or 0

            # Define the barrels you want to purchase based on your inventory needs
            barrels_to_purchase = []

            # Example logic to decide which barrels to purchase
            inventory_query = sqlalchemy.text("""
                SELECT item_id, SUM(change_amount) AS total_ml
                FROM inventory_ledger
                WHERE item_type = 'ml'
                GROUP BY item_id
            """)
            inventory_result = connection.execute(inventory_query).fetchall()

            for inventory in inventory_result:
                ml_needed = 10000 - inventory['total_ml']
                barrels_needed = ml_needed // 1000
                barrel_info_query = sqlalchemy.text("SELECT price FROM barrel_prices WHERE barrel_type = :sku")
                barrel_price = connection.execute(barrel_info_query, {'sku': inventory['item_id']}).scalar()

                if barrel_price is not None:
                    cost_estimate = barrels_needed * barrel_price
                    if current_gold >= cost_estimate:
                        barrels_to_purchase.append({
                            "sku": inventory['item_id'],
                            "ml_per_barrel": 1000,
                            "price": barrel_price,
                            "quantity": barrels_needed
                        })
                        current_gold -= cost_estimate

            # Make the purchase if barrels are needed
            if barrels_to_purchase:
                order_id = generate_order_id(connection)  # Generate a unique order ID
                post_deliver_barrels(barrels_to_purchase, order_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan")
def get_wholesale_purchase_plan():
    try:
        with db.engine.begin() as connection:
            required_inventory = 10000
            inventory_query = sqlalchemy.text("""
                SELECT item_id, SUM(change_amount) AS total_stock
                FROM inventory_ledger
                WHERE item_type = 'ml'
                GROUP BY item_id
            """)
            inventory_result = connection.execute(inventory_query).fetchall()
            purchase_plan = []

            for inventory in inventory_result:
                if inventory['total_stock'] < required_inventory:
                    ml_needed = required_inventory - inventory['total_stock']
                    barrels_needed = ml_needed // 1000
                    barrel_info = connection.execute(sqlalchemy.text("SELECT price FROM potion_mixes WHERE sku = :sku"), {'sku': inventory['item_id']}).scalar()

                    if barrel_info is not None:
                        cost_estimate = barrels_needed * barrel_info
                        purchase_plan.append({"sku": inventory['item_id'], "barrels_needed": barrels_needed, "total_cost": cost_estimate})
                    else:
                        continue

            return purchase_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
