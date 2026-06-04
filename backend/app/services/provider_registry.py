import logging
from app.providers.base import BaseProvider
from app.providers.mock import MockProvider

logger = logging.getLogger(__name__)

_providers: dict[str, BaseProvider] = {}


def _init_providers():
    global _providers
    if _providers:
        return
    _providers["mock"] = MockProvider()
    _init_autodl()


def _init_autodl():
    from app.config import AUTODL_API_KEY
    if AUTODL_API_KEY:
        try:
            from app.providers.autodl import AutoDLProvider
            autodl = AutoDLProvider()
            _providers["autodl"] = autodl
            logger.info("AutoDL provider registered (enabled=%s)", autodl.enabled)
        except Exception:
            logger.warning("Failed to initialize AutoDL provider", exc_info=True)
    else:
        from app.providers.autodl import AutoDLProvider
        _providers["autodl"] = AutoDLProvider()
        logger.info("AutoDL provider registered (no API key, bind mode only)")


_init_providers()


def get_provider(name: str) -> BaseProvider:
    provider = _providers.get(name)
    if provider is None:
        raise ValueError(f"Unknown provider: {name}")
    return provider


def get_active_providers() -> list[BaseProvider]:
    return list(_providers.values())


def get_active_provider_names() -> list[str]:
    return list(_providers.keys())


def is_provider_enabled(name: str) -> bool:
    return name in _providers
