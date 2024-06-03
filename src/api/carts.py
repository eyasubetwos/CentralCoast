from fastapi import APIRouter, Depends, HTTPException
import sqlalchemy
from src import database as db
from pydantic import BaseModel
from src.api import auth
import datetime
import logging

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

# Configure logging
logging.basicConfig(level=logging.INFO)

# Search for cart items
@router.get("/search/", tags=["search"])
def search_orders(customer_name: str = None, item_sku: str = None, cart_id: int = None):
    try:
        with db.engine.begin() as connection:
            query = sqlalchemy.text("""
                SELECT ci.cart_items_id, ci.item_sku, cv.customer_name, ci.quantity, cv.visit_timestamp
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.cart_id
                JOIN customer_visits cv ON c.visit_id = cv.visit_id
                JOIN potion_mixes pm ON ci.item_sku = pm.sku
                WHERE (:customer_name IS NULL OR cv.customer_name ILIKE :customer_name) 
                AND (:item_sku IS NULL OR ci.item_sku = :item_sku)
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

    except Exception as e:
        logging.error(f"Error searching orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{cart_id}/items/")
def set_item_quantity(cart_id: int, cart_item: CartItem):
    try:
        with db.engine.begin() as connection:
            update_query = sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, item_sku, quantity)
                VALUES (:cart_id, :item_sku, :quantity)
                ON CONFLICT (cart_id, item_sku) DO UPDATE SET quantity = EXCLUDED.quantity
            """)
            connection.execute(update_query, {'cart_id': cart_id, 'item_sku': cart_item.item_sku, 'quantity': cart_item.quantity})
            logging.info(f"Cart {cart_id} updated with item {cart_item.item_sku} quantity {cart_item.quantity}")
            return {"status": "Cart updated successfully."}

    except Exception as e:
        logging.error(f"Error updating cart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    try:
        with db.engine.begin() as connection:
            items_query = sqlalchemy.text("""
                SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id
            """)
            items = connection.execute(items_query, {'cart_id': cart_id}).fetchall()

            if not items:
                logging.info(f"No items in cart {cart_id} for checkout.")
                raise HTTPException(status_code=404, detail="No items in cart.")

            total_cost = 0
            for item in items:
                price_query = sqlalchemy.text("SELECT price FROM potion_mixes WHERE sku = :sku")
                price = connection.execute(price_query, {'sku': item['item_sku']}).scalar()
                total_cost += price * item['quantity']
                logging.info(f"Item {item['item_sku']} quantity {item['quantity']} price {price}")

                # Add ledger entry for each item sold
                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('potion', :item_id, -:quantity, 'sale', :date)
                """), {'item_id': item['item_sku'], 'quantity': item['quantity'], 'date': datetime.datetime.now()})

            logging.info(f"Total cost for cart {cart_id}: {total_cost}")

            # Update ledger for gold increase
            connection.execute(sqlalchemy.text("""
                INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                VALUES ('gold', 'N/A', :amount, 'sale income', :date)
            """), {'amount': total_cost, 'date': datetime.datetime.now()})

            logging.info(f"Gold updated with total cost: {total_cost}")

            # Clear the cart after successful transaction
            delete_cart_items_query = sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cart_id")
            connection.execute(delete_cart_items_query, {'cart_id': cart_id})

            logging.info(f"Cart {cart_id} cleared after checkout.")

            return {"total_items_bought": len(items), "total_gold_paid": total_cost}

    except Exception as e:
        logging.error(f"Error during checkout: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate_purchase")
def simulate_purchase():
    try:
        logging.info("Simulating purchase")
        with db.engine.begin() as connection:
            # Add item to cart
            logging.info("Adding item to cart")
            connection.execute(sqlalchemy.text("""
                INSERT INTO cart_items (cart_id, item_sku, quantity) 
                VALUES (1, 'RED_POTION', 1)
                ON CONFLICT (cart_id, item_sku) DO UPDATE SET quantity = EXCLUDED.quantity
            """))
            
            # Perform checkout
            logging.info("Performing checkout")
            items_query = sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id")
            items = connection.execute(items_query, {'cart_id': 1}).fetchall()

            total_cost = 0
            for item in items:
                price_query = sqlalchemy.text("SELECT price FROM potion_mixes WHERE sku = :sku")
                price = connection.execute(price_query, {'sku': item['item_sku']}).scalar()
                total_cost += price * item['quantity']
                
                logging.info(f"Adding ledger entry for {item['item_sku']}")
                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('potion', :item_id, -:quantity, 'sale', :date)
                """), {'item_id': item['item_sku'], 'quantity': item['quantity'], 'date': datetime.datetime.now()})

            logging.info("Updating gold ledger")
            connection.execute(sqlalchemy.text("""
                INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                VALUES ('gold', 'N/A', :amount, 'sale income', :date)
            """), {'amount': total_cost, 'date': datetime.datetime.now()})

            logging.info("Clearing cart")
            connection.execute(sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cart_id"), {'cart_id': 1})

        return {"status": "Simulated purchase completed successfully"}
    except sqlalchemy.exc.SQLAlchemyError as e:
        logging.error(f"Database error during simulated purchase: {e}")
        raise HTTPException(status_code=500, detail="Database error during simulated purchase.")
    except Exception as e:
        logging.error(f"Unexpected error during simulated purchase: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during simulated purchase.")