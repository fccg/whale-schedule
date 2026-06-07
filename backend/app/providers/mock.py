import uuid
from app.providers.base import BaseProvider

MOCK_GPUS = [
    {"id": "mock-a100-1", "provider": "mock", "gpu_family": "A", "gpu_model": "A100-80G",
     "vram_gb": 80.0, "cpu_cores": 16, "memory_gb": 128.0, "disk_gb": 500.0,
     "price_per_hour": 8.50, "currency": "CNY", "region": "Beijing", "available": True},
    {"id": "mock-a100-2", "provider": "mock", "gpu_family": "A", "gpu_model": "A100-40G",
     "vram_gb": 40.0, "cpu_cores": 12, "memory_gb": 96.0, "disk_gb": 400.0,
     "price_per_hour": 6.80, "currency": "CNY", "region": "Shanghai", "available": True},
    {"id": "mock-h800-1", "provider": "mock", "gpu_family": "H", "gpu_model": "H800-80G",
     "vram_gb": 80.0, "cpu_cores": 32, "memory_gb": 256.0, "disk_gb": 1000.0,
     "price_per_hour": 12.00, "currency": "CNY", "region": "Beijing", "available": True},
    {"id": "mock-h800-2", "provider": "mock", "gpu_family": "H", "gpu_model": "H800-80G",
     "vram_gb": 80.0, "cpu_cores": 32, "memory_gb": 256.0, "disk_gb": 800.0,
     "price_per_hour": 11.50, "currency": "CNY", "region": "Shenzhen", "available": True},
    {"id": "mock-h100-1", "provider": "mock", "gpu_family": "H", "gpu_model": "H100-80G",
     "vram_gb": 80.0, "cpu_cores": 32, "memory_gb": 256.0, "disk_gb": 1000.0,
     "price_per_hour": 15.00, "currency": "CNY", "region": "Beijing", "available": True},
    {"id": "mock-6090-1", "provider": "mock", "gpu_family": "RTX", "gpu_model": "RTX 6090",
     "vram_gb": 48.0, "cpu_cores": 16, "memory_gb": 128.0, "disk_gb": 500.0,
     "price_per_hour": 4.50, "currency": "CNY", "region": "Hangzhou", "available": True},
    {"id": "mock-6090-2", "provider": "mock", "gpu_family": "RTX", "gpu_model": "RTX 6090",
     "vram_gb": 48.0, "cpu_cores": 16, "memory_gb": 128.0, "disk_gb": 500.0,
     "price_per_hour": 4.20, "currency": "CNY", "region": "Guangzhou", "available": True},
]


class MockProvider(BaseProvider):
    def __init__(self):
        self._instances: dict[str, dict] = {}

    async def list_gpu_offerings(self) -> list[dict]:
        return [g.copy() for g in MOCK_GPUS]

    async def get_wallet_balance(self) -> dict:
        return {
            "provider": "mock",
            "balance": 9999.0,
            "currency": "CNY",
            "fetched_at": "mock",
        }

    async def create_instance(self, gpu_offering_id: str, config: dict) -> dict:
        instance = {
            "provider_instance_id": str(uuid.uuid4())[:8],
            "gpu_offering_id": gpu_offering_id,
            "status": "provisioning",
            "ssh_host": None,
            "ssh_port": None,
        }
        self._instances[instance["provider_instance_id"]] = instance
        return instance

    async def get_instance(self, instance_id: str) -> dict:
        inst = self._instances.get(instance_id)
        if inst is None:
            return {"provider_instance_id": instance_id, "status": "provisioning"}
        return inst.copy()

    async def destroy_instance(self, instance_id: str) -> bool:
        if instance_id in self._instances:
            self._instances[instance_id]["status"] = "destroyed"
            return True
        self._instances[instance_id] = {"provider_instance_id": instance_id, "status": "destroyed"}
        return True
