from app.models.gpu_offering import get_gpu_offering, get_gpu_offerings, seed_mock_offerings


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
    }
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
        "A100": ["training", "80GB"],
        "H": ["premium", "large-vram"],
        "6090": ["cost-effective", "inference"],
    }
    return mapping.get(family, ["general"])


def _enrich_offering(row: dict) -> dict:
    meta = PROVIDER_META.get(row["provider"], {})
    return {
        **row,
        "gpu_count": 1,
        "host_display_name": f'{meta.get("host_display_name", row["provider"].title())} {row["region"]}',
        "verified": meta.get("verified", False),
        "reliability_score": meta.get("reliability_score", 96.0),
        "network_up_mbps": meta.get("network_up_mbps", 500.0),
        "network_down_mbps": meta.get("network_down_mbps", 900.0),
        "disk_type": meta.get("disk_type", "SSD"),
        "secure_cloud": meta.get("secure_cloud", False),
        "max_duration_days": meta.get("max_duration_days", 3),
        "badge_tags": [*meta.get("badge_tags", []), *_family_badges(row["gpu_family"])],
    }


async def list_market_offerings(
    family: str | None = None,
    provider: str | None = None,
    region: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    search: str | None = None,
    available_only: bool = True,
) -> dict:
    await seed_mock_offerings()
    rows = await get_gpu_offerings(
        family=family,
        provider=provider,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
    )
    items = [_enrich_offering(row) for row in rows]
    if region:
        items = [item for item in items if item["region"] == region]
    if search:
        lowered = search.lower()
        items = [
            item for item in items
            if lowered in item["gpu_model"].lower()
            or lowered in item["region"].lower()
            or lowered in item["provider"].lower()
            or lowered in item["host_display_name"].lower()
        ]
    return {
        "items": items,
        "total": len(items),
        "filters": {
            "families": ["A100", "H", "6090"],
            "providers": ["mock"],
            "regions": sorted({item["region"] for item in items}),
        },
    }


async def get_market_offering(offering_id: str) -> dict | None:
    await seed_mock_offerings()
    row = await get_gpu_offering(offering_id)
    if row is None:
        return None
    return _enrich_offering(row)


async def get_launch_payload(offering_id: str, remaining_budget: float) -> dict | None:
    offering = await get_market_offering(offering_id)
    if offering is None:
        return None
    default_duration_h = 6
    default_disk_gb = max(200, int(offering["disk_gb"] / 2))
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
