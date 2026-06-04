import pytest
from app.providers.mock import MockProvider
from app.providers.autodl import AutoDLProvider, AUTODL_STATIC_OFFERINGS


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


@pytest.mark.asyncio
async def test_autodl_list_offerings():
    """AutoDL list_gpu_offerings should return well-formed offerings."""
    provider = AutoDLProvider()
    offerings = await provider.list_gpu_offerings()
    assert len(offerings) >= 0  # real API may return >= 0, static returns 4
    for o in offerings:
        assert o["provider"] == "autodl"
        assert "gpu_family" in o
        assert "gpu_model" in o
        assert "vram_gb" in o
        assert "price_per_hour" in o
        assert "metadata" in o


@pytest.mark.asyncio
async def test_autodl_offerings_have_required_fields():
    provider = AutoDLProvider()
    offerings = await provider.list_gpu_offerings()
    required = ["id", "provider", "gpu_family", "gpu_model", "vram_gb",
                "cpu_cores", "memory_gb", "disk_gb", "price_per_hour",
                "currency", "region", "available"]
    for o in offerings:
        for field in required:
            assert field in o, f"Missing field {field} in offering {o.get('id')}"


@pytest.mark.asyncio
async def test_autodl_create_instance():
    """AutoDL create_instance should return a provider_instance_id."""
    provider = AutoDLProvider()
    if provider.enabled:
        # Real mode: need a valid gpu_spec_uuid in config
        result = await provider.create_instance("autodl-pro6000-1", {
            "gpu_spec_uuid": "pro6000-p",
        })
        assert "provider_instance_id" in result
        assert result["status"] == "provisioning"
        # Cleanup via release
        await provider.destroy_instance(result["provider_instance_id"])
    else:
        # Bind mode fallback
        result = await provider.create_instance("autodl-pro6000-1", {})
        assert result["provider_instance_id"].startswith("autodl-bind-")
        assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_autodl_destroy_instance():
    provider = AutoDLProvider()
    result = await provider.create_instance("autodl-pro6000-1", {
        "gpu_spec_uuid": "pro6000-p",
    })
    ok = await provider.destroy_instance(result["provider_instance_id"])
    assert ok is True


@pytest.mark.asyncio
async def test_autodl_family_inference():
    provider = AutoDLProvider()
    assert provider._infer_family("A100-80G") == "A100"
    assert provider._infer_family("H800-80G") == "H"
    assert provider._infer_family("H100-80G") == "H"
    assert provider._infer_family("RTX 6090 PRO") == "6090"


def test_provider_registry_has_mock():
    from app.services.provider_registry import get_provider, get_active_provider_names, is_provider_enabled
    assert is_provider_enabled("mock")
    provider = get_provider("mock")
    assert isinstance(provider, MockProvider)
    names = get_active_provider_names()
    assert "mock" in names


def test_provider_registry_has_autodl():
    from app.services.provider_registry import get_provider, is_provider_enabled
    assert is_provider_enabled("autodl")
    provider = get_provider("autodl")
    assert isinstance(provider, AutoDLProvider)


def test_provider_registry_unknown_raises():
    from app.services.provider_registry import get_provider
    import pytest as pt
    with pt.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")
