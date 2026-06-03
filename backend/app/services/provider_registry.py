from app.providers.mock import MockProvider


_providers = {
    "mock": MockProvider(),
}


def get_provider(name: str):
    provider = _providers.get(name)
    if provider is None:
        raise ValueError(f"Unknown provider: {name}")
    return provider


def get_active_providers():
    return list(_providers.values())
