from abc import ABC, abstractmethod


class ProviderError(Exception):
    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider}: {detail}")


class BaseProvider(ABC):

    @abstractmethod
    async def list_gpu_offerings(self) -> list[dict]:
        ...

    @abstractmethod
    async def get_wallet_balance(self) -> dict:
        ...

    @abstractmethod
    async def create_instance(self, gpu_offering_id: str, config: dict) -> dict:
        ...

    @abstractmethod
    async def get_instance(self, instance_id: str) -> dict:
        ...

    @abstractmethod
    async def destroy_instance(self, instance_id: str) -> bool:
        ...
