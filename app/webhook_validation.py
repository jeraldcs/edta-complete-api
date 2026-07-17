from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class WebhookValidationError(ValueError):
    pass


def validate_webhook_target_url(target_url: str) -> str:
    """Validate webhook URLs and block SSRF to private/link-local addresses."""
    parsed = urlparse(target_url.strip())
    if parsed.scheme not in {"https"}:
        raise WebhookValidationError("Webhook target_url must use https.")
    if not parsed.hostname:
        raise WebhookValidationError("Webhook target_url must include a hostname.")
    if parsed.username or parsed.password:
        raise WebhookValidationError("Webhook target_url must not include credentials.")

    hostname = parsed.hostname.lower()
    blocked_hostnames = {"localhost", "metadata.google.internal"}
    if hostname in blocked_hostnames or hostname.endswith(".local"):
        raise WebhookValidationError(f"Webhook hostname is not allowed: {hostname}")

    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise WebhookValidationError("Webhook target_url must not point to a private address.")
    except ValueError:
        try:
            resolved = socket.getaddrinfo(hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror as error:
            raise WebhookValidationError(f"Webhook hostname could not be resolved: {hostname}") from error
        for item in resolved:
            ip = ipaddress.ip_address(item[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise WebhookValidationError(
                    f"Webhook hostname resolves to a private address: {ip}"
                )

    return target_url.strip()
