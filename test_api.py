from httpx import AsyncClient
import pytest
from src.api.server import app  # Adjust the import according to your project structure

headers = {'Authorization': 'key'}

@pytest.mark.asyncio
async def test_get_inventory_audit():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/inventory/audit", headers=headers)
        assert response.status_code == 200
        assert "number_of_potions" in response.json()

@pytest.mark.asyncio
async def test_deliver_barrels():
    test_data = {
        "barrels_delivered": [
            {"sku": "123", "ml_per_barrel": 100, "potion_type": [0, 100, 0, 0], "price": 20, "quantity": 1}
        ],
        "order_id": 1
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/barrels/deliver/1", json=test_data, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "Barrels delivered and inventory updated."}

@pytest.mark.asyncio
async def test_get_bottle_plan():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/bottler/plan", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)  # Adjust according to expected response

