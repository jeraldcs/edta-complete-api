from typing import Any, Protocol


class ProfileLookupAdapter(Protocol):
    """Pluggable profile source for CDP/CRM integration."""

    @property
    def adapter_name(self) -> str: ...

    @property
    def source_label(self) -> str: ...

    def lookup(self, customer_id: str) -> dict[str, Any] | None: ...
