"""Basic health-check test."""

from httpx import AsyncClient, ASGITransport
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test that the health endpoint returns ok."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
