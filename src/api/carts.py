import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = None,
    potion_sku: str = None,
    search_page: str = None,
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Dynamically search for cart line items based on filters and pagination.
    """
    query_base = "SELECT line_item_id, item_sku, customer_name, line_item_total, timestamp FROM orders"
    conditions = []
    values = {}

    if customer_name:
        conditions.append("customer_name ILIKE :customer_name")
        values['customer_name'] = f'%{customer_name}%'
    if potion_sku:
        conditions.append("item_sku = :item_sku")
        values['item_sku'] = potion_sku

    if conditions:
        query_base += " WHERE " + " AND ".join(conditions)

    query_base += f" ORDER BY {sort_col.value} {sort_order.value}"

    # Implement pagination
    if search_page:
        query_base += " OFFSET :offset"
        values['offset'] = (int(search_page) - 1) * 5

    query_base += " LIMIT 5"

    with db.engine.begin() as connection:
        results = connection.execute(sqlalchemy.text(query_base), **values).fetchall()

    formatted_results = [{
        "line_item_id": result[0],
        "item_sku": result[1],
        "customer_name": result[2],
        "line_item_total": result[3],
        "timestamp": result[4].isoformat(),
    } for result in results]

    return {
        "previous": "",  # Placeholder for the previous page token, if applicable.
        "next": "",  # Placeholder for the next page token, if there are more results.
        "results": formatted_results,
    }



class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

from datetime import datetime

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Records which customers visited the shop today.
    """
    with db.engine.begin() as connection:
        for customer in customers:
            # Insert each customer visit into the database
            insert_query = sqlalchemy.text(
                "INSERT INTO customer_visits (visit_id, customer_name, character_class, level, visit_timestamp) "
                "VALUES (:visit_id, :customer_name, :character_class, :level, :visit_timestamp)"
            )
            connection.execute(insert_query, visit_id=visit_id, customer_name=customer.customer_name, 
                               character_class=customer.character_class, level=customer.level, 
                               visit_timestamp=datetime.now())
    
    return {"status": "Customer visits recorded successfully."}


@router.post("/")
def create_cart(new_cart: Customer):
    """
    Create a new cart for a customer, storing it in the database.
    """
    with db.engine.begin() as connection:
        cart_query = "INSERT INTO carts (customer_name, character_class, level) VALUES (:customer_name, :character_class, :level) RETURNING cart_id"
        result = connection.execute(sqlalchemy.text(cart_query), customer_name=new_cart.customer_name, character_class=new_cart.character_class, level=new_cart.level)
        cart_id = result.scalar()

    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """
    Update the quantity of an item in a cart. If the item doesn't exist, add it to the cart.
    """
    with db.engine.begin() as connection:
        # Attempt to update the item quantity if it exists
        update_query = "UPDATE cart_items SET quantity = :quantity WHERE cart_id = :cart_id AND item_sku = :item_sku"
        result = connection.execute(sqlalchemy.text(update_query), cart_id=cart_id, item_sku=item_sku, quantity=cart_item.quantity)

        if result.rowcount == 0:
            # If the item wasn't already in the cart, add it
            insert_query = "INSERT INTO cart_items (cart_id, item_sku, quantity) VALUES (:cart_id, :item_sku, :quantity)"
            connection.execute(sqlalchemy.text(insert_query), cart_id=cart_id, item_sku=item_sku, quantity=cart_item.quantity)

    return {"status": "Item quantity updated."}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """
    Process a cart for checkout, updating inventory and adjusting the shop's gold.
    """
    total_cost = 0
    with db.engine.begin() as connection:
        # Fetch all items in the cart
        cart_items_query = "SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id"
        cart_items = connection.execute(sqlalchemy.text(cart_items_query), cart_id=cart_id).fetchall()

        for item in cart_items:
            # For each item, check inventory and price
            inventory_query = "SELECT num_potions, price FROM inventory WHERE potion_sku = :item_sku"
            inventory_item = connection.execute(sqlalchemy.text(inventory_query), item_sku=item.item_sku).first()

            if not inventory_item or inventory_item.num_potions < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient inventory for {item.item_sku}")

            # Calculate total cost and update inventory
            total_cost += inventory_item.price * item.quantity
            new_inventory = inventory_item.num_potions - item.quantity
            update_inventory_query = "UPDATE inventory SET num_potions = :new_inventory WHERE potion_sku = :item_sku"
            connection.execute(sqlalchemy.text(update_inventory_query), new_inventory=new_inventory, item_sku=item.item_sku)

        # Update shop's gold
        update_gold_query = "UPDATE shop_info SET gold = gold + :total_cost"
        connection.execute(sqlalchemy.text(update_gold_query), total_cost=total_cost)

    return {"total_potions_bought": sum(item.quantity for item in cart_items), 