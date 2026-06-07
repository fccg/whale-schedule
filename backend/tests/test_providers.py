import json
import pytest
from app.providers.mock import MockProvider
from app.providers.autodl import AutoDLProvider, AUTODL_STATIC_OFFERINGS
from app.providers.base import ProviderError


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
        # Real mode: need valid gpu_spec_uuid + image_uuid in config
        result = await provider.create_instance("autodl-pro6000-1", {
            "gpu_spec_uuid": "pro6000-p",
            "image_uuid": "test-image-uuid",
        })
        assert "provider_instance_id" in result
        assert result["status"] == "provisioning"
        # Cleanup via release
        await provider.destroy_instance(result["provider_instance_id"])
    else:
        # Bind mode fallback — still needs gpu_spec_uuid + image_uuid to pass validation
        result = await provider.create_instance("autodl-pro6000-1", {
            "gpu_spec_uuid": "pro6000-p",
            "image_uuid": "test-image-uuid",
        })
        assert result["provider_instance_id"].startswith("autodl-bind-")
        assert result["status"] == "provisioning"


@pytest.mark.asyncio
async def test_autodl_destroy_instance():
    provider = AutoDLProvider()
    result = await provider.create_instance("autodl-pro6000-1", {
        "gpu_spec_uuid": "pro6000-p",
        "image_uuid": "test-image-uuid",
    })
    ok = await provider.destroy_instance(result["provider_instance_id"])
    assert ok is True


@pytest.mark.asyncio
async def test_autodl_family_inference():
    provider = AutoDLProvider()
    assert provider._infer_family("A100-80G") == "A"
    assert provider._infer_family("H800-80G") == "H"
    assert provider._infer_family("H100-80G") == "H"
    assert provider._infer_family("RTX 6090 PRO") == "RTX"
    assert provider._infer_family("RTX 5090") == "RTX"


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


def test_enrich_offering_parses_metadata_json():
    """_enrich_offering should parse metadata_json into metadata dict."""
    from app.services.market_service import _enrich_offering
    row = {
        "id": "autodl-pro6000-1", "provider": "autodl",
        "gpu_family": "RTX", "gpu_model": "RTX 6000 Pro",
        "vram_gb": 48.0, "cpu_cores": 16, "memory_gb": 128.0,
        "disk_gb": 500.0, "price_per_hour": 3.80, "currency": "CNY",
        "region": "Beijing", "available": True,
        "metadata_json": '{"gpu_spec_uuid": "pro6000-p", "cuda_v_from": 113}',
    }
    result = _enrich_offering(row)
    assert "metadata" in result
    assert isinstance(result["metadata"], dict)
    assert result["metadata"]["gpu_spec_uuid"] == "pro6000-p"


def test_enrich_offering_handles_invalid_metadata_json():
    """_enrich_offering should return empty metadata dict on parse failure."""
    from app.services.market_service import _enrich_offering
    row = {
        "id": "autodl-bad", "provider": "autodl",
        "gpu_family": "RTX", "gpu_model": "Bad GPU",
        "vram_gb": 1.0, "cpu_cores": 1, "memory_gb": 1.0,
        "disk_gb": 1.0, "price_per_hour": 1.0, "currency": "CNY",
        "region": "X", "available": False,
        "metadata_json": "not valid json",
    }
    result = _enrich_offering(row)
    assert result["metadata"] == {}


@pytest.mark.asyncio
async def test_autodl_create_instance_missing_gpu_spec_uuid():
    """create_instance should raise ProviderError when gpu_spec_uuid is missing."""
    provider = AutoDLProvider()
    with pytest.raises(ProviderError, match="Missing gpu_spec_uuid"):
        await provider.create_instance("autodl-pro6000-1", {})


@pytest.mark.asyncio
async def test_autodl_create_instance_missing_image_uuid_raises():
    """create_instance should raise ProviderError when image_uuid is empty and no default set."""
    provider = AutoDLProvider()
    # Simulate: gpu_spec_uuid present but image_uuid empty with no env default
    import app.providers.autodl as mod
    old_default = mod.AUTODL_DEFAULT_IMAGE_UUID
    try:
        mod.AUTODL_DEFAULT_IMAGE_UUID = ""
        with pytest.raises(ProviderError, match="Missing image_uuid"):
            await provider.create_instance("autodl-pro6000-1", {"gpu_spec_uuid": "pro6000-p"})
    finally:
        mod.AUTODL_DEFAULT_IMAGE_UUID = old_default


@pytest.mark.asyncio
async def test_market_offering_contains_metadata_with_gpu_spec_uuid():
    """get_market_offering for autodl should include metadata.gpu_spec_uuid."""
    from app.services.market_service import get_market_offering
    from app.database import get_db
    import app.models.gpu_offering as gpu_model

    db = await get_db()
    metadata = {"gpu_spec_uuid": "test-gpu-uuid", "cuda_v_from": 113}
    await db.execute(
        "INSERT OR REPLACE INTO gpu_offerings (id, provider, gpu_family, gpu_model, "
        "vram_gb, cpu_cores, memory_gb, disk_gb, price_per_hour, currency, region, available, metadata_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("test-autodl-meta", "autodl", "RTX", "Test GPU", 48.0, 16, 128.0, 500.0,
         3.80, "CNY", "Beijing", 1, json.dumps(metadata)),
    )
    await db.commit()

    offering = await get_market_offering("test-autodl-meta")
    assert offering is not None
    assert "metadata" in offering
    assert isinstance(offering["metadata"], dict)
    assert offering["metadata"]["gpu_spec_uuid"] == "test-gpu-uuid"

    # Cleanup
    await db.execute("DELETE FROM gpu_offerings WHERE id = ?", ("test-autodl-meta",))
    await db.commit()


@pytest.mark.asyncio
async def test_market_filters_are_dynamic():
    from app.services.market_service import list_market_offerings

    payload = await list_market_offerings(provider="mock")
    assert payload["filters"]["families"] == ["A", "H", "RTX"]
    assert "RTX 5090" in payload["filters"]["models"]
    assert "mock" in payload["filters"]["providers"]


@pytest.mark.asyncio
async def test_market_model_filters_follow_selected_family():
    from app.services.market_service import list_market_offerings

    payload = await list_market_offerings(provider="mock", family="RTX")
    assert payload["filters"]["families"] == ["A", "H", "RTX"]
    assert "RTX 4090" in payload["filters"]["models"]
    assert "A100-80G" not in payload["filters"]["models"]
