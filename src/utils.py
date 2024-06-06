import sqlalchemy
from fastapi import HTTPException
from src import database as db
from src.api.barrels import post_deliver_barrels
import datetime

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
                if ml_needed > 0:
                    barrels_needed = (ml_needed + 999) // 1000  # Ceiling division to get the required number of barrels
                    barrel_info = connection.execute(sqlalchemy.text("SELECT price FROM potion_mixes WHERE sku = :sku"), {'sku': inventory['item_id']}).scalar()

                    if barrel_info is not None:
                        cost_estimate = barrels_needed * barrel_info
                        if current_gold >= cost_estimate:
                            barrels_to_purchase.append({
                                "sku": inventory['item_id'],
                                "ml_per_barrel": 1000,
                                "price": barrel_info,
                                "quantity": barrels_needed
                            })
                            current_gold -= cost_estimate

            # Make the purchase if barrels are needed
            if barrels_to_purchase:
                # Generate a new order_id dynamically
                order_id_query = sqlalchemy.text("SELECT COALESCE(MAX(order_id), 0) + 1 FROM orders")
                order_id = connection.execute(order_id_query).scalar()
                
                # Call post_deliver_barrels with the list of barrels to purchase and the new order_id
                post_deliver_barrels(barrels_to_purchase, order_id)

    except SQLAlchemyError as e:
        logging.error(f"Database error during barrel purchase: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error during barrel purchase.")
    except Exception as e:
        logging.error(f"Unexpected error during barrel purchase: {str(e)}")
        raise HTTPException(status_code=500, detail="Unexpected error during barrel purchase.")