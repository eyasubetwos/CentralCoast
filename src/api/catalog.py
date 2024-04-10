import sqlalchemy
from src import database as db

from fastapi import APIRouter

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        # Retrieve the number of green potions and gold from the inventory
        inventory_query = "SELECT num_green_potions, gold FROM global_inventory"
        result = connection.execute(sqlalchemy.text(inventory_query)).first()
        
        # If there's no result, assume 0 potions and default gold amount
        num_green_potions, gold = result if result else (0, 100)

        # Initialize an empty catalog response
        catalog_response = []

        # If there are green potions available, add them to the catalog response
        if num_green_potions > 0:
            catalog_response.append({
                "sku": "GREEN_POTION",
                "name": "Green Potion",
                "quantity": num_green_potions,
                "price": 50,  # The price of each potion
                "potion_type": [0, 100, 0, 0]  # Represents the type of potion
            })
        
    # Return the catalog response, which will be an empty list if no potions are available
    return catalog_response
