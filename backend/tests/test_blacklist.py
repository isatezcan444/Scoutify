import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_blacklist_add_list_and_bulk_delete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add test number 1
        res1 = await client.post(
            "/api/v1/blacklist",
            json={"phone_e164": "+905551234567", "reason": "USER_REQUEST"}
        )
        assert res1.status_code == 201
        bl1_id = res1.json()["id"]

        # Add test number 2
        res2 = await client.post(
            "/api/v1/blacklist",
            json={"phone_e164": "+905559876543", "reason": "SPAM_COMPLAINT"}
        )
        assert res2.status_code == 201
        bl2_id = res2.json()["id"]

        # List blacklist (paginated response)
        list_res = await client.get("/api/v1/blacklist?page=1&size=20")
        assert list_res.status_code == 200
        data = list_res.json()
        assert "items" in data
        assert "total" in data
        assert "pages" in data
        items = data["items"]
        ids = [i["id"] for i in items]
        assert bl1_id in ids
        assert bl2_id in ids

        # Bulk delete test numbers
        bulk_res = await client.post(
            "/api/v1/blacklist/bulk-delete",
            json={"ids": [bl1_id, bl2_id]}
        )
        assert bulk_res.status_code == 200
        assert bulk_res.json()["deleted_count"] >= 2

        # Verify removal
        post_list_res = await client.get("/api/v1/blacklist")
        assert post_list_res.status_code == 200
        post_ids = [i["id"] for i in post_list_res.json()["items"]]
        assert bl1_id not in post_ids
        assert bl2_id not in post_ids
