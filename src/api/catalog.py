import sqlalchemy
from src import database as db
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        # Retrieve the number of green potions and gold from the inventory
        inventory_query = sqlalchemy.text("SELECT num_green_potions, gold FROM global_inventory")
        result = connection.execute(inventory_query).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        num_green_potions, gold = result
        
        # Initialize an empty catalog response
        catalog_response = []

        # Define potion details in a more dynamic way, assuming potential future expansion
        potion_details = {
            "GREEN_POTION": {
                "name": "Green Potion",
                "price": 50,  # This could be dynamically retrieved from a config or database
                "potion_type": [0, 100, 0, 0]  # Represents the type of potion
            }
        }

        # If there are green potions available, add them to the catalog response
        if num_green_potions > 0:
            catalog_response.append({
                "sku": "GREEN_POTION",
                "name": potion_details["GREEN_POTION"]["name"],
                "quantity": num_green_potions,
                "price": potion_details["GREEN_POTION"]["price"],
                "potion_type": potion_details["GREEN_POTION"]["potion_type"]
            })
        
    # Return the catalog response, which will be an empty list if no potions are available
    return catalog_response
