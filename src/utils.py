import sqlalchemy
from fastapi import HTTPException
from src import database as db
from src.api.barrels import post_deliver_barrels
import datetime

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
