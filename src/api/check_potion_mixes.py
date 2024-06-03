import sqlalchemy
from src import database as db

def check_potion_mixes():
    with db.engine.begin() as connection:
        query = sqlalchemy.text("SELECT * FROM potion_mixes")
        result = connection.execute(query).fetchall()
        for row in result:
            print(row)

check_potion_mixes()
