import asyncio
import json
import logging
from app.models.gpu_offering import get_gpu_offering, get_gpu_offerings, seed_mock_offerings, upsert_gpu_offerings
from app.services.provider_registry import get_active_providers, get_active_provider_names

logger = logging.getLogger(__name__)

PROVIDER_META = {
    "mock": {
        "host_display_name": "Mock Cloud Node",
        "verified": True,
        "reliability_score": 99.2,
        "network_up_mbps": 980.0,
        "network_down_mbps": 1450.0,
        "disk_type": "NVMe SSD",
        "secure_cloud": True,
        "max_duration_days": 7,
        "badge_tags": ["recommended", "instant"],
    },
    "autodl": {
        "host_display_name": "AutoDL Cloud",
        "verified": True,
        "reliability_score": 95.0,
        "network_up_mbps": 500.0,
        "network_down_mbps": 800.0,
        "disk_type": "NVMe SSD",
        "secure_cloud": True,
        "max_duration_days": 14,
        "badge_tags": ["real", "verified"],
    },
}

TEMPLATES = [
    {
        "id": "pytorch",
        "label": "NVIDIA PyTorch",
        "image": "nvidia/pytorch:26.03-py3",
        "description": "开箱即用的深度学习训练环境，预装 CUDA、cuDNN、PyTorch。",
        "highlights": ["PyTorch", "CUDA 13", "Recommended"],
        "recommended": True,
    },
    {
        "id": "cuda-dev",
        "label": "CUDA Dev Base",
        "image": "nvidia/cuda:13.0-devel-ubuntu24.04",
        "description": "适合自定义依赖安装和开发调试的 CUDA 基础镜像。",
        "highlights": ["CUDA 13", "Ubuntu 24.04", "Dev"],
        "recommended": False,
    },
    {
        "id": "ubuntu",
        "label": "Ubuntu Clean",
        "image": "ubuntu:24.04",
        "description": "最小化基础系统，适合自行配置 bootstrap 流程。",
        "highlights": ["Clean", "Custom", "Lightweight"],
        "recommended": False,
    },
]


def _family_badges(family: str) -> list[str]:
    mapping = {
        "A": ["training", "accelerator"],
        "H": ["premium", "large-vram"],
        "RTX": ["cost-effective", "inference"],
    }
    return mapping.get(family, ["general"])


def _enrich_offering(row: dict) -> dict:
    meta = PROVIDER_META.get(row["provider"], {})
    metadata = {}
    metadata_json = row.get("metadata_json")
    if metadata_json and isinstance(metadata_json, str):
        try:
            metadata = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    return {
        **row,
        "metadata": metadata,
        "gpu_count": 1,
        "host_display_name": f'{meta.get("host_display_name", row["provider"].title())} {row.get("region", "")}',
        "verified": meta.get("verified", False),
        "reliability_score": meta.get("reliability_score", 96.0),
        "network_up_mbps": meta.get("network_up_mbps", 500.0),
        "network_down_mbps": meta.get("network_down_mbps", 900.0),
        "disk_type": meta.get("disk_type", "SSD"),
        "secure_cloud": meta.get("secure_cloud", False),
        "max_duration_days": meta.get("max_duration_days", 3),
        "badge_tags": [*meta.get("badge_tags", []), *_family_badges(row.get("gpu_family", "general"))],
    }


async def _sync_provider_offerings():
    """Pull offerings from all active providers and upsert into gpu_offerings table."""
    providers = get_active_providers()
    for provider in providers:
        try:
            offerings = await provider.list_gpu_offerings()
            if offerings:
                await upsert_gpu_offerings(offerings)
        except Exception:
            logger.warning(f"Failed to sync offerings from provider", exc_info=True)


async def list_market_offerings(
    family: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    region: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
    available_only: bool = True,
) -> dict:
    await seed_mock_offerings()
    try:
        await _sync_provider_offerings()
    except Exception:
        logger.warning("Provider sync failed, using cached offerings", exc_info=True)

    rows = await get_gpu_offerings(
        provider=provider,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
    )
    candidate_items = [_enrich_offering(row) for row in rows]
    if region:
        candidate_items = [item for item in candidate_items if item.get("region") == region]
    if search:
        lowered = search.lower()
        candidate_items = [
            item for item in candidate_items
            if lowered in item.get("gpu_model", "").lower()
            or lowered in item.get("region", "").lower()
            or lowered in item.get("provider", "").lower()
            or lowered in item.get("host_display_name", "").lower()
        ]

    families = sorted({item.get("gpu_family", "") for item in candidate_items if item.get("gpu_family")})
    providers = sorted({item.get("provider", "") for item in candidate_items if item.get("provider")})
    all_regions = sorted({item.get("region", "") for item in candidate_items if item.get("region")})
    model_scope = candidate_items if not family else [
        item for item in candidate_items if item.get("gpu_family") == family
    ]
    models = sorted({item.get("gpu_model", "") for item in model_scope if item.get("gpu_model")})

    items = candidate_items
    if family:
        items = [item for item in items if item.get("gpu_family") == family]
    if model:
        items = [item for item in items if item.get("gpu_model") == model]

    return {
        "items": items,
        "total": len(items),
        "filters": {
            "families": families,
            "models": models,
            "providers": providers or get_active_provider_names(),
            "regions": all_regions,
        },
    }


async def get_market_offering(offering_id: str) -> dict | None:
    await seed_mock_offerings()
    try:
        await _sync_provider_offerings()
    except Exception:
        pass
    row = await get_gpu_offering(offering_id)
    if row is None:
        return None
    return _enrich_offering(row)


async def get_launch_payload(offering_id: str, remaining_budget: float) -> dict | None:
    offering = await get_market_offering(offering_id)
    if offering is None:
        return None
    default_duration_h = 6
    default_disk_gb = max(200, int(offering.get("disk_gb", 200) / 2))
    return {
        "offering": offering,
        "templates": TEMPLATES,
        "defaults": {
            "template_id": "pytorch",
            "disk_gb": default_disk_gb,
            "duration_h": default_duration_h,
        },
        "budget": {
            "remaining_budget": round(remaining_budget, 2),
            "estimated_total": round(offering["price_per_hour"] * default_duration_h, 2),
            "price_per_hour": offering["price_per_hour"],
        },
        "recommended_config": {
            "template": "nvidia/pytorch:26.03-py3",
            "disk_gb": default_disk_gb,
            "duration_h": default_duration_h,
        },
    }
