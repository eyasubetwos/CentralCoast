import sqlalchemy
from src import database as db
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    try:
        with db.engine.begin() as connection:
            # Retrieve potion details for all available potion types from the potion_mixes table
            potion_details_query = sqlalchemy.text(
                "SELECT name, sku, price, inventory_quantity, potion_composition FROM potion_mixes"
            )
            results = connection.execute(potion_details_query).fetchall()
            
            if not results:
                raise HTTPException(status_code=404, detail="Potion details not found.")

            # Initialize an empty catalog response
            catalog_response = []

            # Add available potions to the catalog response
            for result in results:
                name, sku, price, inventory_quantity, potion_composition = result

                # Add to catalog only if the potion is available in inventory
                if inventory_quantity > 0:
                    catalog_response.append({
                        "sku": sku,
                        "name": name,
                        "quantity": inventory_quantity,
                        "price": price,
                        "potion_composition": potion_composition
                    })

            return catalog_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
