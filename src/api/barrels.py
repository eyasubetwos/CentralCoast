from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    price: int
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    with db.engine.begin() as connection:
        total_cost = sum(barrel.price * barrel.quantity for barrel in barrels_delivered)
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        if current_gold < total_cost:
            raise HTTPException(status_code=400, detail="Not enough gold to complete the transaction.")

        for barrel in barrels_delivered:
            # Fetch potion information from the database based on SKU
            potion_mix = connection.execute(
                sqlalchemy.text("SELECT id, inventory_quantity FROM potion_mixes WHERE sku = :sku"),
                {'sku': barrel.sku}
            ).first()

            if potion_mix is None:
                raise HTTPException(status_code=404, detail=f"Potion with SKU {barrel.sku} not found.")
            
            # Update inventory level in potion_mixes table
            new_inventory_quantity = potion_mix.inventory_quantity + (barrel.quantity)
            connection.execute(
                sqlalchemy.text("UPDATE potion_mixes SET inventory_quantity = :new_inventory_quantity WHERE id = :id"),
                {'new_inventory_quantity': new_inventory_quantity, 'id': potion_mix.id}
            )
            
            # Deduct the cost of barrels from the gold in global_inventory table
            connection.execute(
                sqlalchemy.text("UPDATE global_inventory SET gold = gold - :spent_gold WHERE id = 1"),
                {'spent_gold': barrel.price * barrel.quantity}
            )

        return {"status": f"Barrels delivered and inventory updated for order_id {order_id}"}


@router.post("/plan")
def get_wholesale_purchase_plan():
    with db.engine.begin() as connection:
        # Fetch potion information from potion_mixes and potion_capacity tables
        inventory_query = sqlalchemy.text("""
            SELECT p.sku, p.inventory_quantity, p.price, c.max_capacity
            FROM potion_mixes p
            JOIN potion_capacity c ON p.sku = c.potion_sku
        """)
        potion_data = connection.execute(inventory_query).fetchall()
        
        # Define thresholds and business rules parameters
        restock_threshold = 500
        minimum_restock = 100
        budget_limit = 10000  # Example budget limit for restocking
        
        purchase_plan = []
        total_estimated_cost = 0
        
        # Determine what needs to be restocked based on inventory levels and business rules
        for potion in potion_data:
            if potion.inventory_quantity < restock_threshold:
                # Basic restock amount based on the minimum restock level and the threshold
                restock_amount = max(minimum_restock, restock_threshold - potion.inventory_quantity)
                    
                # Estimate cost for this restock and add to total
                restock_cost = restock_amount * potion.price
                total_estimated_cost += restock_cost
                
                # Check if the estimated cost is within the budget
                if total_estimated_cost <= budget_limit:
                    purchase_plan.append({"sku": potion.sku, "restock_amount": restock_amount})
                else:
                    # If the budget limit is reached, break the loop
                    break

        return purchase_plan
