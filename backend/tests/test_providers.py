import pytest
from app.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_list_offerings():
    provider = MockProvider()
    offerings = await provider.list_gpu_offerings()
    assert len(offerings) == 7
    assert offerings[0]["gpu_model"] == "A100-80G"


@pytest.mark.asyncio
async def test_mock_create_instance():
    provider = MockProvider()
    result = await provider.create_instance("mock-a100-1", {"template": "test", "disk_gb": 100})
    assert "provider_instance_id" in result
    assert len(result["provider_instance_id"]) == 8


@pytest.mark.asyncio
async def test_mock_get_instance():
    provider = MockProvider()
    created = await provider.create_instance("mock-a100-1", {})
    result = await provider.get_instance(created["provider_instance_id"])
    assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_mock_destroy_instance():
    provider = MockProvider()
    created = await provider.create_instance("mock-a100-1", {})
    ok = await provider.destroy_instance(created["provider_instance_id"])
    assert ok is True
    result = await provider.get_instance(created["provider_instance_id"])
    assert result["status"] == "destroyed"
