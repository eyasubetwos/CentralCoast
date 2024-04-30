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
                "SELECT name, sku, price, potion_composition FROM potion_mixes"
            )
            results = connection.execute(potion_details_query).fetchall()
            
            if not results:
                raise HTTPException(status_code=404, detail="Potion details not found.")

            # Initialize an empty catalog response
            catalog_response = []

            # Calculate inventory quantity for each potion from the ledger
            for result in results:
                name, sku, price, potion_composition = result

                # Fetch the total quantity for the current potion SKU from the ledger
                ledger_query = sqlalchemy.text(
                    "SELECT SUM(change_amount) AS total_quantity FROM inventory_ledger WHERE item_id = :sku"
                )
                ledger_result = connection.execute(ledger_query, {'sku': sku}).scalar()

                inventory_quantity = ledger_result if ledger_result is not None else 0

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