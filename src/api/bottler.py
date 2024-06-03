import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import datetime


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
                # Checking the composition directly against the database to find the matching SKU
                potion_query = sqlalchemy.text("""
                    SELECT sku FROM potion_mixes WHERE potion_composition = :composition
                """)
                potion_result = connection.execute(potion_query, {'composition': potion.potion_composition}).first()
                
                if potion_result:
                    sku = potion_result['sku']
                    # Insert a ledger entry to increase the inventory
                    connection.execute(sqlalchemy.text("""
                        INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                        VALUES ('potion', :sku, :quantity, 'bottling', :date)
                    """), {'sku': sku, 'quantity': 1, 'date': datetime.datetime.now()})  # Assuming quantity 1 for simplification
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
            potion_mixes_query = sqlalchemy.text("SELECT * FROM potion_mixes")
            potion_mixes_result = connection.execute(potion_mixes_query).fetchall()

            bottling_plan = []
            for mix in potion_mixes_result:
                # Assuming each bottle requires a certain amount of ml which should be checked against the ledger
                required_ml = 100  # Simplified assumption
                current_inventory_query = sqlalchemy.text("""
                    SELECT SUM(change_amount) AS total_ml
                    FROM inventory_ledger
                    WHERE item_id = :sku AND item_type = 'ml'
                """)
                current_inventory = connection.execute(current_inventory_query, {'sku': mix['sku']}).scalar()
                
                if current_inventory >= required_ml:
                    # Calculate the quantity of each potion type based on the inventory and maximum capacity
                    max_potions = current_inventory // required_ml
                    if max_potions > 0:
                        bottling_plan.append({"potion_type": mix['potion_composition'], "quantity": max_potions})

            return bottling_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))