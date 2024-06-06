from fastapi import APIRouter, HTTPException, Depends
import sqlalchemy
from src import database as db
from src.api import auth
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
import logging

logging.basicConfig(level=logging.DEBUG)

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

@router.get("/audit")
def get_inventory():
    try:
        with db.engine.begin() as connection:
            # Fetch initial values from global_inventory
            global_inventory_query = sqlalchemy.text("""
                SELECT gold, num_red_ml, num_green_ml, num_blue_ml, num_red_potions, num_green_potions, num_blue_potions
                FROM global_inventory
                WHERE id = 1
            """)
            global_inventory = connection.execute(global_inventory_query).fetchone()
            if not global_inventory:
                raise HTTPException(status_code=500, detail="Global inventory not initialized.")

            # Initialize totals with global inventory values
            inventory_totals = {
                'gold': global_inventory['gold'],
                'red_ml': global_inventory['num_red_ml'],
                'green_ml': global_inventory['num_green_ml'],
                'blue_ml': global_inventory['num_blue_ml'],
                'red_potions': global_inventory['num_red_potions'],
                'green_potions': global_inventory['num_green_potions'],
                'blue_potions': global_inventory['num_blue_potions'],
            }

            # Sum up the changes from the inventory_ledger table
            ledger_query = sqlalchemy.text("""
                SELECT item_type, item_id, SUM(change_amount) AS total
                FROM inventory_ledger
                GROUP BY item_type, item_id
            """)
            ledger_result = connection.execute(ledger_query).fetchall()

            # Update totals based on ledger entries
            for item in ledger_result:
                item_type = item['item_type']
                item_id = item['item_id']
                total = item['total']

                if item_type == 'gold':
                    inventory_totals['gold'] += total
                elif item_type == 'ml':
                    if item_id == 'red':
                        inventory_totals['red_ml'] += total
                    elif item_id == 'green':
                        inventory_totals['green_ml'] += total
                    elif item_id == 'blue':
                        inventory_totals['blue_ml'] += total
                elif item_type == 'potion':
                    if item_id == 'RP-001':
                        inventory_totals['red_potions'] += total
                    elif item_id == 'GP-001':
                        inventory_totals['green_potions'] += total
                    elif item_id == 'BP-001':
                        inventory_totals['blue_potions'] += total

            # Get details for each potion type
            potion_query = sqlalchemy.text("SELECT name, sku, price, potion_composition FROM potion_mixes")
            potion_result = connection.execute(potion_query).fetchall()
            potions = [
                {
                    "name": potion[0],
                    "sku": potion[1],
                    "price": potion[2],
                    "inventory_quantity": inventory_totals.get(potion[1], 0),
                    "potion_composition": potion[3]
                } for potion in potion_result
            ]

            return {
                "inventory": potions,
                "gold": inventory_totals['gold'],
                "ml": {
                    "red": inventory_totals['red_ml'],
                    "green": inventory_totals['green_ml'],
                    "blue": inventory_totals['blue_ml']
                },
                "potions": {
                    "red": inventory_totals['red_potions'],
                    "green": inventory_totals['green_potions'],
                    "blue": inventory_totals['blue_potions']
                }
            }

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/plan")
def get_capacity_plan():
    """
    Calculate how much additional potion and ml capacity can be bought with available gold.
    Each unit costs 1000 gold. Assumes no partial purchases are allowed.
    """
    with db.engine.begin() as connection:
        gold_query = sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
        current_gold = connection.execute(gold_query).scalar()
        cost_query = sqlalchemy.text("SELECT gold_cost_per_unit FROM capacity_inventory WHERE id = 1")
        cost_per_unit = connection.execute(cost_query).scalar()

        if current_gold is None or cost_per_unit is None:
            raise HTTPException(status_code=404, detail="Required inventory data not found.")

        additional_units = current_gold // cost_per_unit
        additional_potion_capacity = additional_units * 50
        additional_ml_capacity = additional_units * 10000 

        return {
            "current_gold": current_gold,
            "cost_per_unit": cost_per_unit,
            "additional_potion_capacity": additional_potion_capacity,
            "additional_ml_capacity": additional_ml_capacity
        }

@router.post("/deliver/{order_id}")
def deliver_capacity_plan(order_id: int):
    """
    Automatically purchase additional capacity for potions and ml based on available gold.
    Each unit costs 1000 gold and provides 50 potion slots and 10000 ml.
    """
    try:
        with db.engine.begin() as connection:
            # Fetch the current amount of gold from the inventory_ledger table
            gold_query = sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
            current_gold = connection.execute(gold_query).scalar() or 0
            
            # Fetch the cost per unit of capacity from the capacity_inventory table
            cost_query = sqlalchemy.text("SELECT gold_cost_per_unit FROM capacity_inventory WHERE id = 1")
            cost_per_unit = connection.execute(cost_query).scalar()

            if cost_per_unit is None:
                raise HTTPException(status_code=404, detail="Required inventory data not found.")

            # Calculate how many additional units of capacity can be bought
            additional_units = current_gold // cost_per_unit

            # Update the shop's capacity based on the additional units that can be afforded
            connection.execute(sqlalchemy.text("""
                UPDATE capacity_inventory SET
                potion_capacity = potion_capacity + :additional_units * 50,
                ml_capacity = ml_capacity + :additional_units * 10000
                WHERE id = 1
            """), {'additional_units': additional_units})

            # Deduct the cost of the capacity from the gold
            connection.execute(sqlalchemy.text("""
                INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                VALUES ('gold', 'N/A', -:cost, 'Capacity purchase', :date)
            """), {'cost': additional_units * cost_per_unit, 'date': datetime.datetime.now()})

            # Sync global inventory with ledger
            sync_global_inventory()

            return {"status": "OK", "message": f"Capacity purchased and inventory updated for order_id {order_id}"}
    
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

