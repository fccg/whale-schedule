import asyncio
import json
import logging
from app.models.gpu_offering import get_gpu_offering, get_gpu_offerings, seed_mock_offerings, upsert_gpu_offerings
from app.services.budget_service import get_provider_budget_config, get_provider_budget_remaining
from app.services.provider_registry import get_provider
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

GENERIC_TEMPLATES = [
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

AUTODL_TEMPLATES = [
    {
        "id": "autodl-pytorch-2-0-cuda11-8",
        "label": "PyTorch 2.0 / CUDA 11.8",
        "image": "cuda11.8-cudnn8-devel-ubuntu20.04-py38-torch2.0.0",
        "image_uuid": "base-image-l2t43iu6uk",
        "framework": "PyTorch",
        "description": "推荐用于主流训练与推理任务，兼顾兼容性和稳定性。",
        "highlights": ["PyTorch", "CUDA 11.8", "Ubuntu 20.04"],
        "recommended": True,
    },
    {
        "id": "autodl-pytorch-1-11-cuda11-3",
        "label": "PyTorch 1.11 / CUDA 11.3",
        "image": "cuda11.3-cudnn8-devel-ubuntu20.04-py38-torch1.11.0",
        "image_uuid": "base-image-l374uiucui",
        "framework": "PyTorch",
        "description": "适合偏保守依赖栈或旧项目迁移场景。",
        "highlights": ["PyTorch", "CUDA 11.3", "Ubuntu 20.04"],
        "recommended": False,
    },
    {
        "id": "autodl-pytorch-1-10-cuda11-3",
        "label": "PyTorch 1.10 / CUDA 11.3",
        "image": "cuda11.3-cudnn8-devel-ubuntu20.04-py38-torch1.10.0",
        "image_uuid": "base-image-u9r24vthlk",
        "framework": "PyTorch",
        "description": "适合需要较老 PyTorch 版本的训练脚本。",
        "highlights": ["PyTorch", "CUDA 11.3", "Python 3.8"],
        "recommended": False,
    },
    {
        "id": "autodl-pytorch-1-9-cuda11-1",
        "label": "PyTorch 1.9 / CUDA 11.1",
        "image": "cuda11.1-cudnn8-devel-ubuntu18.04-py38-torch1.9.0",
        "image_uuid": "base-image-12be412037",
        "framework": "PyTorch",
        "description": "适合更老的训练环境与兼容性排障。",
        "highlights": ["PyTorch", "CUDA 11.1", "Ubuntu 18.04"],
        "recommended": False,
    },
    {
        "id": "autodl-tensorflow-2-9-cuda11-2",
        "label": "TensorFlow 2.9 / CUDA 11.2",
        "image": "cuda11.2-cudnn8-devel-ubuntu20.04-py38-tf2.9.0",
        "image_uuid": "base-image-uxeklgirir",
        "framework": "TensorFlow",
        "description": "适合常见 TensorFlow 训练与推理工作负载。",
        "highlights": ["TensorFlow", "CUDA 11.2", "Ubuntu 20.04"],
        "recommended": False,
    },
    {
        "id": "autodl-tensorflow-2-5-cuda11-2",
        "label": "TensorFlow 2.5 / CUDA 11.2",
        "image": "cuda11.2-cudnn8-devel-ubuntu18.04-py38-tf2.5.0",
        "image_uuid": "base-image-0gxqmciyth",
        "framework": "TensorFlow",
        "description": "适合较老 TensorFlow 工程与兼容场景。",
        "highlights": ["TensorFlow", "CUDA 11.2", "Ubuntu 18.04"],
        "recommended": False,
    },
    {
        "id": "autodl-tensorflow-1-15-cuda11-4",
        "label": "TensorFlow 1.15 / CUDA 11.4",
        "image": "cuda11.4-py38-tf1.15.5",
        "image_uuid": "base-image-4bpg0tt88l",
        "framework": "TensorFlow",
        "description": "适合仍依赖 TensorFlow 1.x 的老项目维护。",
        "highlights": ["TensorFlow", "CUDA 11.4", "Python 3.8"],
        "recommended": False,
    },
    {
        "id": "autodl-miniconda-cuda11-6",
        "label": "Miniconda / CUDA 11.6",
        "image": "cuda11.6-cudnn8-devel-ubuntu20.04-py38",
        "image_uuid": "base-image-mbr2n4urrc",
        "framework": "Miniconda",
        "description": "适合自定义依赖安装和环境管理。",
        "highlights": ["Miniconda", "CUDA 11.6", "Ubuntu 20.04"],
        "recommended": False,
    },
    {
        "id": "autodl-miniconda-cuda11-3-gl",
        "label": "Miniconda / CUDA GL 11.3",
        "image": "cudagl11.3-cudnn8-devel-ubuntu20.04-py38",
        "image_uuid": "base-image-7bn8iqhkb5",
        "framework": "Miniconda",
        "description": "适合需要图形栈或可视化依赖的容器环境。",
        "highlights": ["Miniconda", "CUDA GL 11.3", "Ubuntu 20.04"],
        "recommended": False,
    },
    {
        "id": "autodl-miniconda-cuda11-1",
        "label": "Miniconda / CUDA 11.1",
        "image": "cuda11.1-cudnn8-devel-ubuntu18.04-py38",
        "image_uuid": "base-image-h041hn36yt",
        "framework": "Miniconda",
        "description": "适合较老 CUDA 依赖的自定义环境。",
        "highlights": ["Miniconda", "CUDA 11.1", "Ubuntu 18.04"],
        "recommended": False,
    },
    {
        "id": "autodl-miniconda-cuda10-2",
        "label": "Miniconda / CUDA 10.2",
        "image": "cuda10.2-cudnn7-devel-ubuntu18.04-py38",
        "image_uuid": "base-image-qkkhitpik5",
        "framework": "Miniconda",
        "description": "适合必须固定在 CUDA 10.2 的老项目。",
        "highlights": ["Miniconda", "CUDA 10.2", "Ubuntu 18.04"],
        "recommended": False,
    },
    {
        "id": "autodl-miniconda-cuda9-0",
        "label": "Miniconda / CUDA 9.0",
        "image": "cuda9.0-cudnn7-devel-ubuntu16.04-py36",
        "image_uuid": "base-image-k0vep6kyq8",
        "framework": "Miniconda",
        "description": "仅用于极老依赖栈排障或兼容需求。",
        "highlights": ["Miniconda", "CUDA 9.0", "Ubuntu 16.04"],
        "recommended": False,
    },
    {
        "id": "autodl-tensorrt-8-5-cuda11-8",
        "label": "TensorRT 8.5 / CUDA 11.8",
        "image": "cuda11.8-cudnn8-devel-ubuntu20.04-py38-trt8.5.1",
        "image_uuid": "base-image-l2843iu23k",
        "framework": "TensorRT",
        "description": "适合 TensorRT 推理优化与部署验证。",
        "highlights": ["TensorRT", "CUDA 11.8", "Ubuntu 20.04"],
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


def get_launch_templates(offering: dict) -> list[dict]:
    if offering.get("provider") == "autodl":
        return [template.copy() for template in AUTODL_TEMPLATES]
    return [template.copy() for template in GENERIC_TEMPLATES]


def get_recommended_template(offering: dict) -> dict:
    templates = get_launch_templates(offering)
    for template in templates:
        if template.get("recommended"):
            return template
    return templates[0]


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


def _resolve_limiting_factor(wallet_balance: float, provider_budget_remaining: float | None) -> str:
    if provider_budget_remaining is None:
        return "none"
    return "wallet" if wallet_balance <= provider_budget_remaining else "provider_budget"


async def build_funding_summary(offering: dict, duration_h: int) -> dict:
    estimated_total = round(offering["price_per_hour"] * duration_h, 2)
    provider_name = offering["provider"]
    provider = get_provider(provider_name)
    wallet = await provider.get_wallet_balance()
    wallet_balance = round(float(wallet["balance"]), 2)
    provider_budget_config = await get_provider_budget_config(provider_name)
    provider_budget_remaining = await get_provider_budget_remaining(provider_name)
    provider_budget_enabled = provider_budget_remaining is not None

    if provider_budget_remaining is None:
        effective_available = wallet_balance
    else:
        effective_available = min(wallet_balance, round(provider_budget_remaining, 2))

    return {
        "provider": provider_name,
        "estimated_total": estimated_total,
        "wallet_balance": wallet_balance,
        "wallet_currency": wallet.get("currency", offering.get("currency", "CNY")),
        "provider_budget_enabled": provider_budget_enabled,
        "provider_budget_total": round(float(provider_budget_config["total_budget"]), 2)
        if provider_budget_enabled and provider_budget_config and provider_budget_config.get("total_budget") is not None
        else None,
        "provider_budget_remaining": round(provider_budget_remaining, 2) if provider_budget_remaining is not None else None,
        "effective_available": round(effective_available, 2),
        "limiting_factor": _resolve_limiting_factor(wallet_balance, provider_budget_remaining),
    }


async def get_launch_payload(offering_id: str) -> dict | None:
    offering = await get_market_offering(offering_id)
    if offering is None:
        return None
    default_duration_h = 6
    default_disk_gb = max(200, int(offering.get("disk_gb", 200) / 2))
    templates = get_launch_templates(offering)
    recommended_template = get_recommended_template(offering)
    funding = await build_funding_summary(offering, default_duration_h)
    return {
        "offering": offering,
        "templates": templates,
        "defaults": {
            "template_id": recommended_template["id"],
            "disk_gb": default_disk_gb,
            "duration_h": default_duration_h,
        },
        "funding": funding,
        "budget": {
            "remaining_budget": funding["provider_budget_remaining"],
            "estimated_total": funding["estimated_total"],
            "price_per_hour": offering["price_per_hour"],
        },
        "recommended_config": {
            "template_id": recommended_template["id"],
            "template": recommended_template["image"],
            "image_uuid": recommended_template.get("image_uuid"),
            "disk_gb": default_disk_gb,
            "duration_h": default_duration_h,
        },
    }
