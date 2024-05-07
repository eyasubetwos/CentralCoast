import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import datetime
from json import dumps


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
                potion_query = sqlalchemy.text("SELECT sku FROM potion_mixes WHERE potion_composition = :composition")
                potion_result = connection.execute(potion_query, {'composition': dumps(potion.potion_composition)}).first()
                
                if potion_result:
                    sku = potion_result['sku']
                    connection.execute(sqlalchemy.text("""
                        INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                        VALUES ('potion', :sku, 1, 'bottling', :date)
                    """), {'sku': sku, 'date': datetime.datetime.now()})
                else:
                    logging.warning(f"No matching potion composition found for {potion.potion_composition}")
                    raise HTTPException(status_code=404, detail=f"Potion mix with composition {potion.potion_composition} not found.")
        logging.info(f"Potions delivered for order_id {order_id}")
        return {"status": f"Potions delivered and inventory updated for order_id {order_id}."}
    except Exception as e:
        logging.error(f"Error delivering potions for order_id {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan")
def get_bottle_plan():
    try:
        with db.engine.begin() as connection:
            potion_mixes_query = sqlalchemy.text("SELECT * FROM potion_mixes")
            potion_mixes_result = connection.execute(potion_mixes_query).fetchall()

            bottling_plan = []
            for mix in potion_mixes_result:
                required_ml = 100
                current_inventory_query = sqlalchemy.text("""
                    SELECT SUM(change_amount) AS total_ml
                    FROM inventory_ledger
                    WHERE item_id = :sku AND item_type = 'ml'
                """)
                current_inventory = connection.execute(current_inventory_query, {'sku': mix['sku']}).scalar()

                if current_inventory and current_inventory >= required_ml:
                    max_potions = current_inventory // required_ml
                    if max_potions > 0:
                        bottling_plan.append({"potion_type": mix['potion_composition'], "quantity": max_potions})

            return bottling_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))