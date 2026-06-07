import json
import logging
from datetime import datetime, timezone
import httpx
from app.config import (
    AUTODL_API_BASE,
    AUTODL_API_KEY,
    AUTODL_DEFAULT_IMAGE_UUID,
    AUTODL_DEFAULT_CUDA_V_FROM,
    AUTODL_DEFAULT_GPU_AMOUNT,
    AUTODL_DEFAULT_SYSTEM_DISK_GB,
    AUTODL_DATA_CENTER_LIST,
)
from app.providers.base import BaseProvider, ProviderError

logger = logging.getLogger(__name__)

AUTODL_GPU_SPEC_UUID_RULES = (
    (("4090D",), "4090D"),
    (("H80080G", "H800"), "h800"),
    (("PRO600096G", "RTX6000PRO", "PRO6000"), "pro6000-p"),
    (("4080S32G", "RTX4080S", "4080S"), "v-32g-p"),
    (("309048G", "RTX3090", "3090"), "v-48g-350w"),
    (("509032G", "RTX5090", "5090"), "5090-p"),
    (("409048G", "RTX4090", "4090"), "v-48g"),
)

AUTODL_STATIC_OFFERINGS = [
    {
        "id": "autodl-pro6000-1", "provider": "autodl",
        "gpu_family": "RTX", "gpu_model": "PRO6000-96G",
        "vram_gb": 96.0, "cpu_cores": 16, "memory_gb": 128.0,
        "disk_gb": 500.0, "price_per_hour": 3.80, "currency": "CNY",
        "region": "Beijing", "available": True,
        "metadata": {
            "gpu_spec_uuid": "pro6000-p",
            "cuda_v_from": AUTODL_DEFAULT_CUDA_V_FROM,
        },
    },
    {
        "id": "autodl-4090-1", "provider": "autodl",
        "gpu_family": "RTX", "gpu_model": "4090-48G",
        "vram_gb": 48.0, "cpu_cores": 16, "memory_gb": 96.0,
        "disk_gb": 500.0, "price_per_hour": 3.20, "currency": "CNY",
        "region": "Beijing", "available": True,
        "metadata": {
            "gpu_spec_uuid": "v-48g",
            "cuda_v_from": AUTODL_DEFAULT_CUDA_V_FROM,
        },
    },
    {
        "id": "autodl-5090-1", "provider": "autodl",
        "gpu_family": "RTX", "gpu_model": "5090-32G",
        "vram_gb": 32.0, "cpu_cores": 20, "memory_gb": 128.0,
        "disk_gb": 600.0, "price_per_hour": 4.10, "currency": "CNY",
        "region": "Shanghai", "available": True,
        "metadata": {
            "gpu_spec_uuid": "5090-p",
            "cuda_v_from": AUTODL_DEFAULT_CUDA_V_FROM,
        },
    },
    {
        "id": "autodl-h800-1", "provider": "autodl",
        "gpu_family": "H", "gpu_model": "H800-80G",
        "vram_gb": 80.0, "cpu_cores": 32, "memory_gb": 256.0,
        "disk_gb": 1000.0, "price_per_hour": 16.00, "currency": "CNY",
        "region": "Beijing", "available": True,
        "metadata": {
            "gpu_spec_uuid": "h800",
            "cuda_v_from": AUTODL_DEFAULT_CUDA_V_FROM,
        },
    },
]


class AutoDLProvider(BaseProvider):
    def __init__(self):
        self._api_base = AUTODL_API_BASE.rstrip("/")
        self._api_key = AUTODL_API_KEY
        self._enabled = bool(self._api_key)
        self._instances: dict[str, dict] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _headers(self) -> dict:
        return {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self._api_base}{path}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            if method == "GET":
                if body:
                    resp = await client.request("GET", url, headers=self._headers(), content=json.dumps(body))
                else:
                    resp = await client.get(url, headers=self._headers())
            else:
                resp = await client.request(method, url, headers=self._headers(), json=body)
            if resp.status_code >= 400:
                raise ProviderError("autodl", f"HTTP {resp.status_code}: {resp.text[:300]}")
            try:
                return resp.json()
            except json.JSONDecodeError:
                raise ProviderError("autodl", f"Invalid JSON response: {resp.text[:300]}")

    @staticmethod
    def _ensure_success(resp: dict, action: str) -> dict:
        code = resp.get("code")
        if code and code != "Success":
            msg = resp.get("msg", "unknown error")
            raise ProviderError("autodl", f"{action} failed [{code}]: {msg}")
        data = resp.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _normalize_gpu_model(model_name: str) -> str:
        return "".join(ch for ch in model_name.upper() if ch.isalnum())

    @classmethod
    def _resolve_gpu_spec_uuid(cls, model_name: str, provider_gpu_spec_uuid: str = "") -> str:
        normalized = cls._normalize_gpu_model(model_name)
        for tokens, gpu_spec_uuid in AUTODL_GPU_SPEC_UUID_RULES:
            if any(token in normalized for token in tokens):
                return gpu_spec_uuid
        return provider_gpu_spec_uuid

    async def get_wallet_balance(self) -> dict:
        if not self._enabled:
            raise ProviderError("autodl", "Wallet balance unavailable without AUTODL_API_KEY")

        try:
            resp = await self._request("POST", "/api/v1/dev/wallet/balance", {})
            data = self._ensure_success(resp, "Wallet balance")
            assets = data.get("assets")
            if assets is None:
                raise ProviderError("autodl", "Wallet balance response missing assets")
            balance = float(assets) / 1000.0
            return {
                "provider": "autodl",
                "balance": balance,
                "currency": "CNY",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("autodl", f"Get wallet balance error: {str(e)}")

    async def list_gpu_offerings(self) -> list[dict]:
        if not self._enabled:
            return [g.copy() for g in AUTODL_STATIC_OFFERINGS]
        try:
            resp = await self._request("POST", "/api/v1/dev/instance/pro/list", {
                "page_index": 1, "page_size": 50,
            })
            data_block = resp.get("data", {})
            if isinstance(data_block, dict):
                instances = data_block.get("list", [])
            elif isinstance(data_block, list):
                instances = data_block
            else:
                instances = []
            offerings = []
            for inst in instances:
                offerings.append(self._map_instance_to_offering(inst))
            return offerings if offerings else [g.copy() for g in AUTODL_STATIC_OFFERINGS]
        except Exception:
            logger.warning("AutoDL list API failed, falling back to static offerings", exc_info=True)
            return [g.copy() for g in AUTODL_STATIC_OFFERINGS]

    def _map_instance_to_offering(self, inst: dict) -> dict:
        uuid = inst.get("uuid", inst.get("instance_uuid", ""))
        gpu_alias = inst.get("machine_alias", "") or inst.get("snapshot_gpu_alias_name", "") or inst.get("gpu_spec_uuid", "GPU")
        gpu_spec_uuid = self._resolve_gpu_spec_uuid(gpu_alias, inst.get("gpu_spec_uuid", ""))
        gpu_family = self._infer_family(gpu_alias)
        status = inst.get("status", inst.get("instance_status", ""))
        return {
            "id": f"autodl-{uuid}",
            "provider": "autodl",
            "gpu_family": gpu_family,
            "gpu_model": gpu_alias,
            "vram_gb": float(inst.get("gpu_vram_gb", 48)),
            "cpu_cores": int(inst.get("vcpu", 16)),
            "memory_gb": float(inst.get("memory_gb", 128)),
            "disk_gb": float(inst.get("system_disk_gb", 500)),
            "price_per_hour": float(inst.get("payg_price", 0)) / 1000.0,
            "currency": "CNY",
            "region": inst.get("region_sign", inst.get("region_name", "Unknown")),
            "available": status in ("running", "available"),
            "metadata": {
                "gpu_spec_uuid": gpu_spec_uuid,
                "instance_uuid": uuid,
                "cuda_v_from": AUTODL_DEFAULT_CUDA_V_FROM,
                "status": status,
            },
        }

    @staticmethod
    def _infer_family(model_name: str) -> str:
        m = model_name.upper()
        if any(x in m for x in ("H100", "H800", "H20")):
            return "H"
        if any(x in m for x in ("A100", "A800", "A40", "A5000", "A6000")):
            return "A"
        if any(x in m for x in ("RTX", "4090", "5090", "6000 PRO", "PRO6000")):
            return "RTX"
        return "RTX"

    async def create_instance(self, gpu_offering_id: str, config: dict) -> dict:
        gpu_spec_uuid = config.get("gpu_spec_uuid", "")
        image_uuid = config.get("image_uuid", AUTODL_DEFAULT_IMAGE_UUID)
        if not image_uuid:
            image_uuid = AUTODL_DEFAULT_IMAGE_UUID
        if not gpu_spec_uuid:
            raise ProviderError("autodl", "Missing gpu_spec_uuid for create_instance")
        if not image_uuid:
            raise ProviderError("autodl", "Missing image_uuid for create_instance")
        body = {
            "req_gpu_amount": config.get("gpu_amount", AUTODL_DEFAULT_GPU_AMOUNT),
            "expand_system_disk_by_gb": config.get("expand_system_disk_by_gb", AUTODL_DEFAULT_SYSTEM_DISK_GB),
            "gpu_spec_uuid": gpu_spec_uuid,
            "image_uuid": image_uuid,
            "cuda_v_from": config.get("cuda_v_from", AUTODL_DEFAULT_CUDA_V_FROM),
            "instance_name": config.get("instance_name", "schedule-instance"),
            "start_command": config.get("start_command", "sleep 1"),
        }
        if AUTODL_DATA_CENTER_LIST:
            body["data_center_list"] = [d.strip() for d in AUTODL_DATA_CENTER_LIST.split(",") if d.strip()]

        logger.info("Autodl create_instance request: gpu_spec_uuid=%s, image_uuid=%s, cuda_v_from=%s, req_gpu_amount=%s, instance_name=%s",
                    gpu_spec_uuid, image_uuid, body.get("cuda_v_from"), body.get("req_gpu_amount"), body.get("instance_name"))

        if not self._enabled:
            import uuid
            provider_instance_id = f"autodl-bind-{uuid.uuid4().hex[:8]}"
            self._instances[provider_instance_id] = {
                "provider_instance_id": provider_instance_id,
                "gpu_offering_id": gpu_offering_id,
                "status": "provisioning",
                "ssh_host": None,
                "ssh_port": None,
            }
            return {
                "provider_instance_id": provider_instance_id,
                "status": "provisioning",
                "ssh_host": None,
                "ssh_port": None,
                "connect_url": None,
                "jupyter_url": None,
                "region": None,
                "hourly_price": None,
            }

        try:
            resp = await self._request("POST", "/api/v1/dev/instance/pro/create", body)
            if resp.get("code") != "Success":
                code = resp.get("code", "UNKNOWN")
                msg = resp.get("msg", "unknown error")
                raise ProviderError("autodl", f"Create failed [{code}]: {msg}")
            provider_instance_id = resp["data"]
            instance_data = {
                "provider_instance_id": provider_instance_id,
                "status": "provisioning",
                "ssh_host": None,
                "ssh_port": None,
                "connect_url": None,
                "jupyter_url": None,
                "region": None,
                "hourly_price": None,
            }
            self._instances[provider_instance_id] = instance_data
            return instance_data
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("autodl", f"Create instance error: {str(e)}")

    async def get_instance(self, instance_id: str) -> dict:
        if not self._enabled:
            inst = self._instances.get(instance_id, {})
            return inst if inst else {"provider_instance_id": instance_id, "status": "unknown"}

        try:
            resp = await self._request("POST", "/api/v1/dev/instance/pro/list", {
                "page_index": 1, "page_size": 100,
            })
            data_block = resp.get("data", {})
            instances = data_block.get("list", []) if isinstance(data_block, dict) else []
            for inst in instances:
                if inst.get("uuid") == instance_id or inst.get("instance_uuid") == instance_id:
                    status = inst.get("status", "unknown")
                    return {
                        "provider_instance_id": instance_id,
                        "status": status,
                        "ssh_host": inst.get("proxy_host"),
                        "ssh_port": inst.get("ssh_port"),
                        "connect_url": inst.get("ssh_command"),
                        "jupyter_url": inst.get("jupyter_domain"),
                        "region": inst.get("region_sign"),
                        "hourly_price": float(inst.get("payg_price", 0)) / 1000.0,
                        "gpu_model": inst.get("machine_alias", ""),
                        "raw": inst,
                    }
            return {"provider_instance_id": instance_id, "status": "not_found"}
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError("autodl", f"Get instance error: {str(e)}")

    async def destroy_instance(self, instance_id: str) -> bool:
        if not self._enabled:
            self._instances.pop(instance_id, None)
            return True

        power_off_ok = False
        shutdown_confirmed = False
        release_ok = False

        # ---- Phase 1: power_off ----
        try:
            power_resp = await self._request("POST", "/api/v1/dev/instance/pro/power_off", {
                "instance_uuid": instance_id,
            })
            if power_resp.get("code") == "Success":
                power_off_ok = True
            else:
                logger.warning("AutoDL power_off rejected for %s: code=%s msg=%s",
                               instance_id, power_resp.get("code"), power_resp.get("msg"))
        except Exception:
            logger.warning("AutoDL power_off request failed for %s", instance_id, exc_info=True)

        # ---- Phase 2: poll for shutdown, then release ----
        import asyncio
        poll_count = 0
        while poll_count < 30:
            poll_count += 1
            try:
                list_resp = await self._request("POST", "/api/v1/dev/instance/pro/list", {
                    "page_index": 1, "page_size": 100,
                })
                data_block = list_resp.get("data", {})
                instances = data_block.get("list", []) if isinstance(data_block, dict) else []
                target = None
                for inst in instances:
                    if inst.get("uuid") == instance_id or inst.get("instance_uuid") == instance_id:
                        target = inst
                        break

                if target is None:
                    # Instance gone from list — already released or never existed
                    logger.info("AutoDL destroy[%s]: instance not found in list, treating as already released", instance_id)
                    release_ok = True
                    break

                current_status = target.get("status", "")
                if current_status == "shutdown":
                    shutdown_confirmed = True
                    rel_resp = await self._request("POST", "/api/v1/dev/instance/pro/release", {
                        "instance_uuid": instance_id,
                    })
                    if rel_resp.get("code") == "Success":
                        release_ok = True
                        logger.info("AutoDL destroy[%s]: power_off=%s shutdown=%s release=Success",
                                    instance_id, power_off_ok, shutdown_confirmed)
                    else:
                        logger.warning("AutoDL destroy[%s]: release rejected code=%s msg=%s",
                                       instance_id, rel_resp.get("code"), rel_resp.get("msg"))
                    break
                elif current_status in ("shutting_down",):
                    await asyncio.sleep(3)
                    continue
                else:
                    # still running or other — wait for power_off to take effect
                    await asyncio.sleep(3)
                    continue
            except Exception:
                await asyncio.sleep(3)
                continue

        # ---- Phase 3: summary ----
        if release_ok:
            logger.info("AutoDL destroy[%s]: REMOTE_RELEASED (power_off=%s shutdown=%s release=%s)",
                        instance_id, power_off_ok, shutdown_confirmed, release_ok)
        else:
            logger.warning("AutoDL destroy[%s]: LOCAL_CLEANUP_ONLY — remote release NOT confirmed "
                           "(power_off=%s shutdown=%s release=%s). Verify AutoDL console.",
                           instance_id, power_off_ok, shutdown_confirmed, release_ok)

        self._instances.pop(instance_id, None)
        return release_ok
