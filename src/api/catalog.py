import sqlalchemy
from src import database as db
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        # Retrieve the inventory details for all potion types from the inventory
        inventory_query = sqlalchemy.text(
            "SELECT num_green_potions, num_red_potions, num_blue_potions, gold FROM global_inventory"
        )
        result = connection.execute(inventory_query).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Inventory data not found.")

        # Unpack all potion quantities and gold
        num_green_potions, num_red_potions, num_blue_potions, gold = result
        
        # Initialize an empty catalog response
        catalog_response = []

        # Define potion details for each potion type
        potion_types = {
            "GREEN_POTION": {
                "name": "Green Potion",
                "quantity": num_green_potions,
                "price": 50,  # Example price
                "potion_type": [0, 100, 0, 0]  # Potion composition
            },
            "RED_POTION": {
                "name": "Red Potion",
                "quantity": num_red_potions,
                "price": 75,  # Example price
                "potion_type": [100, 0, 0, 0]  # Potion composition
            },
            "BLUE_POTION": {
                "name": "Blue Potion",
                "quantity": num_blue_potions,
                "price": 65,  # Example price
                "potion_type": [0, 0, 100, 0]  # Potion composition
            }
        }

        # Add available potions to the catalog response
        for sku, details in potion_types.items():
            if details["quantity"] > 0:  # Add to catalog only if the potion is available
                catalog_response.append({
                    "sku": sku,
                    "name": details["name"],
                    "quantity": details["quantity"],
                    "price": details["price"],
                    "potion_type": details["potion_type"]
                })
        
        # Return the catalog response
        return catalog_response