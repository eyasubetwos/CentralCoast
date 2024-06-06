from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import datetime
import logging

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
def post_deliver_barrels(barrels_delivered: list[dict], order_id: int):
    try:
        with db.engine.begin() as connection:
            total_cost = sum(barrel['price'] * barrel['quantity'] for barrel in barrels_delivered)
            current_gold_query = sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
            current_gold = connection.execute(current_gold_query).scalar() or 0

            if current_gold < total_cost:
                raise HTTPException(status_code=400, detail="Not enough gold to complete the transaction.")

            for barrel in barrels_delivered:
                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('ml', :sku, :change_amount, 'barrel delivery', :date)
                """), {'sku': barrel['sku'], 'change_amount': barrel['ml_per_barrel'] * barrel['quantity'], 'date': datetime.datetime.now()})

                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('gold', 'N/A', -:cost, 'barrel purchase', :date)
                """), {'cost': barrel['price'] * barrel['quantity'], 'date': datetime.datetime.now()})

        logging.info(f"Barrels delivered and inventory updated for order_id {order_id}")
        return {"status": f"Barrels delivered and inventory updated for order_id {order_id}"}
    except SQLAlchemyError as e:
        logging.error(f"Database error during barrel delivery: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error during barrel delivery.")
    except Exception as e:
        logging.error(f"Unexpected error during barrel delivery: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during barrel delivery.")



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
                    barrel_info = connection.execute(sqlalchemy.text("SELECT price FROM barrel_prices WHERE sku = :sku"), {'sku': inventory['item_id']}).scalar()

                    if barrel_info is not None:
                        cost_estimate = barrels_needed * barrel_info
                        purchase_plan.append({"sku": inventory['item_id'], "barrels_needed": barrels_needed, "total_cost": cost_estimate})
                    else:
                        continue

            return purchase_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
