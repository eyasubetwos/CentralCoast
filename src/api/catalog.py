import sqlalchemy
from src import database as db

from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        inventory_query = "SELECT num_green_potions, gold FROM global_inventory"
        result = connection.execute(sqlalchemy.text(inventory_query)).first()
        num_green_potions, gold = result if result else (0, 100)

        catalog_response = [{
            "sku": "GREEN_POTION",
            "name": "Green Potion",
            "quantity": num_green_potions,
            "price": 50,  
            "potion_type": [0, 100, 0, 0]  
        }]
        
    return catalog_response