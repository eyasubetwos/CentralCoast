import os
import dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session
import datetime

def database_connection_url():
    dotenv.load_dotenv()
    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)
metadata = MetaData()

# Define the potion_mixes table
potion_mixes = Table(
    "potion_mixes",
    metadata,
    autoload_with=engine,
)

# Define the inventory_ledger table
inventory_ledger = Table(
    "inventory_ledger",
    metadata,
    autoload_with=engine,
)

def find_one_potion_mix(potion_composition):
    """
    Retrieve a potion mix by its composition from the potion_mixes table.
    """
    with engine.connect() as conn:
        query = potion_mixes.select().where(potion_mixes.c.potion_composition == potion_composition)
        return conn.execute(query).fetchone()

def find_all_potion_mixes():
    """
    Retrieve all potion mixes from the potion_mixes table.
    """
    with engine.connect() as conn:
        query = potion_mixes.select()
        return conn.execute(query).fetchall()

def update_potion_mix(sku, update_fields):
    """
    Record changes to a potion mix in the inventory_ledger instead of updating directly.
    """
    with engine.begin() as conn:
        # Assuming update_fields contains 'inventory_quantity' and possibly 'price'
        if 'inventory_quantity' in update_fields:
            quantity_change = update_fields['inventory_quantity']
            current_quantity = conn.execute(
                sqlalchemy.text("SELECT inventory_quantity FROM potion_mixes WHERE sku = :sku"),
                {'sku': sku}
            ).scalar()
            conn.execute(inventory_ledger.insert(), {
                'item_type': 'potion',
                'item_id': sku,
                'change_amount': quantity_change,
                'current_total': current_quantity + quantity_change,
                'description': 'Inventory update',
                'date': datetime.datetime.now()
            })
        if 'price' in update_fields:
            conn.execute(
                potion_mixes.update().where(potion_mixes.c.sku == sku).values(price=update_fields['price'])
            )

def record_gold_transaction(change_amount, description):
    """
    Record a gold transaction in the inventory_ledger.
    """
    with engine.begin() as conn:
        current_gold = conn.execute(
            sqlalchemy.text("SELECT SUM(change_amount) FROM inventory_ledger WHERE item_type = 'gold'")
        ).scalar() or 0
        conn.execute(inventory_ledger.insert(), {
            'item_type': 'gold',
            'item_id': 'N/A',
            'change_amount': change_amount,
            'current_total': current_gold + change_amount,
            'description': description,
            'date': datetime.datetime.now()
        })
