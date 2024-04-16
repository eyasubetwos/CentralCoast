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
    item_sku: str  # SKU must correspond to specific potion types e.g., 'GREEN_POTION', 'RED_POTION', 'BLUE_POTION'

class CartCheckout(BaseModel):
    payment: str

# Search for cart items
@router.get("/search/", tags=["search"])
def search_orders(customer_name: str = None, item_sku: str = None, cart_id: int = None):
    with db.engine.begin() as connection:
        query = sqlalchemy.text("""
            SELECT ci.cart_items_id, ci.items_sku, cv.customer_name, ci.quantity, cv.visit_timestamp
            FROM cart_items ci
            JOIN carts c ON ci.cart_id = c.cart_id
            JOIN customer_visits cv ON c.visit_id = cv.visit_id
            WHERE (:customer_name IS NULL OR cv.customer_name ILIKE :customer_name) 
            AND (:item_sku IS NULL OR ci.items_sku = :item_sku)
            AND (:cart_id IS NULL OR ci.cart_id = :cart_id)
        """)
        params = {
            'customer_name': f"%{customer_name}%" if customer_name else None,
            'item_sku': item_sku,
            'cart_id': cart_id
        }
        results = connection.execute(query, params).fetchall()

        formatted_results = [{
            "line_item_id": result[0],
            "item_sku": result[1],
            "customer_name": result[2],
            "quantity": result[3],
            "timestamp": result[4].isoformat(),
        } for result in results]

        return formatted_results

# Add item to cart
@router.post("/{cart_id}/items/")
def set_item_quantity(cart_id: int, cart_item: CartItem):
    with db.engine.begin() as connection:
        update_query = sqlalchemy.text("""
            INSERT INTO cart_items (cart_id, items_sku, quantity) 
            VALUES (:cart_id, :items_sku, :quantity)
            ON CONFLICT (cart_id, items_sku) DO UPDATE SET quantity = :quantity
        """)
        # Properly passing parameters as a dictionary
        params = {
            'cart_id': cart_id,
            'items_sku': cart_item.item_sku,
            'quantity': cart_item.quantity
        }
        connection.execute(update_query, params)  # Pass parameters as a dictionary

        return {"status": "Cart updated successfully."}


# Checkout cart
@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        items_query = sqlalchemy.text("""
            SELECT items_sku, quantity FROM cart_items WHERE cart_id = :cart_id
        """)
        items = connection.execute(items_query, cart_id=cart_id).fetchall()

        if not items:
            raise HTTPException(status_code=404, detail="No items in cart.")

        total_cost = 0

        for item in items:
            # Fetch the current inventory based on SKU
            inventory_query = sqlalchemy.text("""
                SELECT price, num_green_potions, num_red_potions, num_blue_potions
                FROM global_inventory
                WHERE id = 1  # Assuming a single global inventory record
            """)
            inventory_item = connection.execute(inventory_query).first()

            if not inventory_item:
                raise HTTPException(status_code=400, detail=f"Item not found: {item.item_sku}")

            potion_count = {
                'GREEN_POTION': inventory_item.num_green_potions,
                'RED_POTION': inventory_item.num_red_potions,
                'BLUE_POTION': inventory_item.num_blue_potions
            }

            available_quantity = potion_count.get(item.item_sku, 0)

            if available_quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.item_sku}")

            total_cost += inventory_item.price * item.quantity

            # Update the inventory
            update_inventory_query = sqlalchemy.text(f"""
                UPDATE global_inventory
                SET {item.item_sku.lower()} = {item.item_sku.lower()} - :quantity
                WHERE id = 1
            """)
            connection.execute(update_inventory_query, quantity=item.quantity)

        # Update the shop's gold
        update_gold_query = sqlalchemy.text("""
            UPDATE global_inventory SET gold = gold + :total_cost
        """)
        connection.execute(update_gold_query, total_cost=total_cost)

        # Clear the cart after successful transaction
        delete_cart_items_query = sqlalchemy.text("""
            DELETE FROM cart_items WHERE cart_id = :cart_id
        """)
        connection.execute(delete_cart_items_query, cart_id=cart_id)

        return {
            "total_potions_bought": sum(item.quantity for item in items),
            "total_gold_paid": total_cost
        }