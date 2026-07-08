from app.config import settings
from app.profile.adapters.base import ProfileLookupAdapter
from app.profile.adapters.json_file import JsonFileProfileAdapter


def build_profile_adapter() -> ProfileLookupAdapter:
    adapter_name = settings.profile_lookup_adapter.lower()
    if adapter_name == "json_file":
        return JsonFileProfileAdapter(settings.profile_lookup_file)
    raise ValueError(f"Unsupported PROFILE_LOOKUP_ADAPTER: {adapter_name}")
