from fastapi import APIRouter, Depends, HTTPException
import sqlalchemy
from src import database as db
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class CartItem(BaseModel):
    quantity: int
    item_sku: str

class CartCheckout(BaseModel):
    payment: str

# Search for cart items
@router.get("/search/", tags=["search"])
def search_orders(customer_name: str = None, item_sku: str = None):
    with db.engine.begin() as connection:
        query = sqlalchemy.text("""
            SELECT line_item_id, item_sku, customer_name, line_item_total, timestamp 
            FROM cart_items 
            WHERE (:customer_name IS NULL OR customer_name ILIKE :customer_name) 
            AND (:item_sku IS NULL OR item_sku = :item_sku)
        """)
        results = connection.execute(query, customer_name=f"%{customer_name}%" if customer_name else None, item_sku=item_sku).fetchall()

        formatted_results = [{
            "line_item_id": result[0],
            "item_sku": result[1],
            "customer_name": result[2],
            "line_item_total": result[3],
            "timestamp": result[4].isoformat(),
        } for result in results]

        return formatted_results

# Add item to cart
@router.post("/{cart_id}/items/")
def set_item_quantity(cart_id: int, cart_item: CartItem):
    with db.engine.begin() as connection:
        update_query = sqlalchemy.text("""
            INSERT INTO cart_items (cart_id, item_sku, quantity) 
            VALUES (:cart_id, :item_sku, :quantity)
            ON CONFLICT (cart_id, item_sku) DO UPDATE SET quantity = :quantity
        """)
        connection.execute(update_query, cart_id=cart_id, item_sku=cart_item.item_sku, quantity=cart_item.quantity)

        return {"status": "Cart updated successfully."}

# Checkout cart
@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        items_query = sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id")
        items = connection.execute(items_query, cart_id=cart_id).fetchall()

        if not items:
            raise HTTPException(status_code=404, detail="No items in cart.")

        total_cost = 0
        for item in items:
            price_query = sqlalchemy.text("SELECT price FROM inventory WHERE item_sku = :item_sku")
            price_result = connection.execute(price_query, item_sku=item.item_sku).first()
            if not price_result:
                raise HTTPException(status_code=404, detail=f"Item {item.item_sku} not found.")
            total_cost += price_result[0] * item.quantity

        # Reduce stock and update financials
        for item in items:
            update_inventory_query = sqlalchemy.text("""
                UPDATE inventory SET num_potions = num_potions - :quantity 
                WHERE item_sku = :item_sku AND num_potions >= :quantity
            """)
            update_result = connection.execute(update_inventory_query, item_sku=item.item_sku, quantity=item.quantity)
            if update_result.rowcount == 0:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.item_sku}.")

        update_gold_query = sqlalchemy.text("UPDATE shop_info SET gold = gold + :total_cost")
        connection.execute(update_gold_query, total_cost=total_cost)

        return {"total_potions_bought": sum(item.quantity for item in items), "total_gold_paid": total_cost}
