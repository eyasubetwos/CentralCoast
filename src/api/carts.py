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
        results = connection.execute(query, customer_name=f"%{customer_name}%" if customer_name else None, item_sku=item_sku, cart_id=cart_id).fetchall()

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
        connection.execute(update_query, cart_id=cart_id, items_sku=cart_item.item_sku, quantity=cart_item.quantity)

        return {"status": "Cart updated successfully."}

# Checkout cart
@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    with db.engine.begin() as connection:
        # Retrieve all items in the cart
        items_query = sqlalchemy.text("""
            SELECT items_sku, quantity FROM cart_items WHERE cart_id = :cart_id
        """)
        items = connection.execute(items_query, cart_id=cart_id).fetchall()

        # Check if the cart is empty
        if not items:
            raise HTTPException(status_code=404, detail="No items in cart.")

        total_cost = 0

        # Check inventory and calculate total cost
        for item in items:
            inventory_query = sqlalchemy.text("""
                SELECT num_green_potions, price FROM global_inventory
                WHERE item_sku = :item_sku
            """)
            inventory_item = connection.execute(inventory_query, item_sku=item.item_sku).first()

            # Check if the item exists and if sufficient quantity is available
            if not inventory_item or inventory_item.num_green_potions < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {item.item_sku}")

            # Calculate the total cost based on the price and quantity
            total_cost += inventory_item.price * item.quantity

            # Deduct the sold quantity from the inventory
            new_inventory = inventory_item.num_green_potions - item.quantity
            update_inventory_query = sqlalchemy.text("""
                UPDATE global_inventory SET num_green_potions = :new_inventory
                WHERE item_sku = :item_sku
            """)
            connection.execute(update_inventory_query, new_inventory=new_inventory, item_sku=item.item_sku)

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
