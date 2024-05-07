from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, paginate
import sqlalchemy
from src import database as db
from pydantic import BaseModel
from src.api import auth
import datetime

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

# Response model for pagination
class OrderItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    quantity: int
    timestamp: str

# Search for cart items with pagination
@router.get("/search/", response_model=Page[OrderItem], tags=["search"])
def search_orders(
    customer_name: str = Query(None),
    item_sku: str = Query(None),
    cart_id: int = Query(None),
    skip: int = Query(0, alias="offset"),
    limit: int = Query(10, alias="limit"),
    sort: str = Query("visit_timestamp", alias="sort")
):
    try:
        with db.engine.begin() as connection:
            # Validate sort parameter
            valid_sort_fields = ['visit_timestamp', 'customer_name', 'item_sku', 'quantity']
            if sort not in valid_sort_fields:
                raise HTTPException(status_code=400, detail="Invalid sort field")

            base_query = """
                SELECT ci.cart_items_id, ci.item_sku, cv.customer_name, ci.quantity, cv.visit_timestamp
                FROM cart_items ci
                JOIN carts c ON ci.cart_id = c.cart_id
                JOIN customer_visits cv ON c.visit_id = cv.visit_id
                JOIN potion_mixes pm ON ci.item_sku = pm.sku
                WHERE (:customer_name IS NULL OR cv.customer_name ILIKE :customer_name) 
                AND (:item_sku IS NULL OR ci.item_sku = :item_sku)
                AND (:cart_id IS NULL OR ci.cart_id = :cart_id)
            """
            # Dynamic sorting
            base_query += f" ORDER BY {sort} OFFSET :skip LIMIT :limit"

            results = connection.execute(sqlalchemy.text(base_query), {
                'customer_name': f"%{customer_name}%" if customer_name else None,
                'item_sku': item_sku,
                'cart_id': cart_id,
                'skip': skip,
                'limit': limit
            }).fetchall()

            formatted_results = [OrderItem(
                line_item_id=result[0],
                item_sku=result[1],
                customer_name=result[2],
                quantity=result[3],
                timestamp=result[4].isoformat()
            ) for result in results]

            return paginate(formatted_results)

    except Exception as e:
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
            return {"status": "Cart updated successfully."}

    except Exception as e:
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
                raise HTTPException(status_code=404, detail="No items in cart.")

            total_cost = 0
            for item in items:
                price_query = sqlalchemy.text("SELECT price FROM potion_mixes WHERE sku = :sku")
                price = connection.execute(price_query, {'sku': item['item_sku']}).scalar()
                total_cost += price * item['quantity']
                # Add ledger entry for each item sold
                connection.execute(sqlalchemy.text("""
                    INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                    VALUES ('potion', :item_id, -:quantity, 'sale', :date)
                """), {'item_id': item['item_sku'], 'quantity': item['quantity'], 'date': datetime.datetime.now()})

            # Update ledger for gold increase
            connection.execute(sqlalchemy.text("""
                INSERT INTO inventory_ledger (item_type, item_id, change_amount, description, date)
                VALUES ('gold', 'N/A', :amount, 'sale income', :date)
            """), {'amount': total_cost, 'date': datetime.datetime.now()})

            # Clear the cart after successful transaction
            delete_cart_items_query = sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cart_id")
            connection.execute(delete_cart_items_query, {'cart_id': cart_id})

            return {"total_items_bought": len(items), "total_gold_paid": total_cost}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
