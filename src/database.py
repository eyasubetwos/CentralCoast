import os
import dotenv
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session

def database_connection_url():
    dotenv.load_dotenv()
    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)
metadata = MetaData()

# Define the potion_mixes table
potion_mixes = Table(
    "potion_mixes",
    metadata,
    autoload_with=engine,  # Add this line
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
    Update a potion mix in the potion_mixes table.
    """
    with engine.begin() as conn:
        query = (
            potion_mixes.update()
            .where(potion_mixes.c.sku == sku)
            .values(update_fields)
        )
        conn.execute(query)
