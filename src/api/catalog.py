import sqlalchemy
from src import database as db

from fastapi import APIRouter

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Dynamically fetches the catalog from the global_inventory table,
    focusing on green potions.
    """
    with db.engine.begin() as connection:
        # Fetch the current state of green potions and gold
        inventory_query = "SELECT num_green_potions, gold FROM global_inventory"
        result = connection.execute(sqlalchemy.text(inventory_query)).first()
        
        # If there's no inventory data, assume initialization state
        num_green_potions, gold = result if result else (0, 100)

        catalog_response = [{
            "sku": "GREEN_POTION",
            "name": "Green Potion",
            "quantity": num_green_potions,
            "price": 50,  # Assuming a flat price; adjust as needed
            "potion_type": [0, 100, 0, 0]  # Representing green potion composition
        }]
        
    return catalog_response