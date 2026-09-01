"""
Final Adversarial API Fuzzing Suite.
Exhaustively tests FastAPI endpoints against malformed payloads, injection attempts,
type confusions, boundary limits, and unexpected characters.
CRITICAL INVARIANT: The API must return structured 4xx responses and NEVER produce HTTP 500.
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_adversarial_api_fuzzing_all_endpoints():
    """
    Fuzzes multiple core endpoints with hostile, oversized, and type-confused inputs.
    Asserts status_code != 500 across all permutations.
    """
    fuzz_payloads = [
        {},  # Completely empty
        {"name": None, "phone": None},  # Explicit nulls
        {"name": "", "phone": ""},  # Empty strings
        {"name": "   ", "phone": "   "},  # Whitespace only
        {"name": "A" * 10000, "phone": "5" * 500},  # Oversized strings
        {"name": "🦷🏥🔥🎉🚀", "phone": "+905321234567"},  # Emojis in text
        {"name": "Admin' OR '1'='1' --", "phone": "05321112233; DROP TABLE leads;--"},  # SQLi
        {"name": "<script>alert('xss')</script>", "phone": "<img src=x onerror=alert(1)>"},  # XSS
        {"name": "../../../../../etc/passwd", "phone": "../.."},  # Path traversal
        {"name": 12345, "phone": 98765},  # Type confusion (integers for strings)
        {"name": ["unexpected", "list"], "phone": {"nested": "dict"}},  # Structured types for primitives
        {"name": "Valid Name", "phone": "-905321234567"},  # Negative phone
        {"name": "Valid Name", "phone": "0000000000"},  # Zero string
        {"name": "Valid Name", "extra_unrecognized_field": "injected_value" * 100},  # Extra fields
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fuzz /api/v1/leads POST
        for p in fuzz_payloads:
            res = await client.post("/api/v1/leads", json=p)
            assert res.status_code != 500, f"Leads POST returned 500 on fuzz: {p} (Response: {res.text})"

        # 2. Fuzz /api/v1/campaign-groups POST
        for p in fuzz_payloads:
            res = await client.post("/api/v1/campaign-groups", json=p)
            assert res.status_code != 500, f"Campaign-Groups POST returned 500 on fuzz: {p} (Response: {res.text})"

        # 3. Fuzz /api/v1/campaigns POST
        for p in fuzz_payloads:
            res = await client.post("/api/v1/campaigns", json=p)
            assert res.status_code != 500, f"Campaigns POST returned 500 on fuzz: {p} (Response: {res.text})"

        # 4. Fuzz /api/v1/settings/antiban PATCH
        for p in fuzz_payloads:
            res = await client.patch("/api/v1/settings/antiban", json=p)
            assert res.status_code != 500, f"Antiban PATCH returned 500 on fuzz: {p} (Response: {res.text})"

        # 5. Fuzz /api/v1/blacklist POST
        for p in fuzz_payloads:
            res = await client.post("/api/v1/blacklist", json=p)
            assert res.status_code != 500, f"Blacklist POST returned 500 on fuzz: {p} (Response: {res.text})"


@pytest.mark.asyncio
async def test_adversarial_invalid_paths_and_identifiers():
    """
    Tests extreme and invalid resource IDs on parameterized REST routes.
    """
    invalid_ids = [
        "0",
        "-1",
        "-999999",
        "2147483647",  # Max 32-bit int
        "9223372036854775800",  # Near 64-bit max int
        "abc",
        "null",
        "undefined",
        "../../admin",
        "%00",  # Null byte
        "' OR '1'='1",
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for bad_id in invalid_ids:
            # Leads
            res = await client.get(f"/api/v1/leads/{bad_id}")
            assert res.status_code in (400, 404, 422), f"Lead GET bad ID {bad_id} got status {res.status_code}"

            # Campaigns
            res = await client.get(f"/api/v1/campaigns/{bad_id}")
            assert res.status_code in (400, 404, 422), f"Campaign GET bad ID {bad_id} got status {res.status_code}"

            # Campaign Groups
            res = await client.get(f"/api/v1/campaign-groups/{bad_id}")
            assert res.status_code in (400, 404, 422), f"Group GET bad ID {bad_id} got status {res.status_code}"

            # Conversations
            res = await client.get(f"/api/v1/conversations/{bad_id}")
            assert res.status_code in (400, 404, 422), f"Conversation GET bad ID {bad_id} got status {res.status_code}"
