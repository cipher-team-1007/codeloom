"""
URL Validator for preventing SSRF vulnerabilities and validating scan targets.
"""
import socket
import urllib.parse
from typing import Tuple


class URLValidator:
    """Validates URLs for safety, scheme, and host restrictions."""

    PRIVATE_IP_PREFIXES = (
        "10.",
        "192.168.",
        "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
        "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
        "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
        "127.",
        "0.",
        "169.254.", # Link-local
    )

    def __init__(self, allow_localhost: bool = True):
        self.allow_localhost = allow_localhost

    def validate(self, url: str) -> Tuple[bool, str]:
        """
        Validates URL string.
        Returns (is_valid: bool, reason_if_invalid: str)
        """
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"

        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return False, "Only HTTP and HTTPS protocols are supported"

        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return False, "Malformed URL format"

        hostname = parsed.hostname
        if not hostname:
            return False, "URL missing domain or host"

        hostname_lower = hostname.lower()

        # Check local/internal hosts
        if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            if not self.allow_localhost:
                return False, "Scanning localhost or local IP targets is restricted"
            return True, "Valid"

        # Check private IPs if host is literal IP
        for prefix in self.PRIVATE_IP_PREFIXES:
            if hostname_lower.startswith(prefix):
                if not self.allow_localhost:
                    return False, "Scanning private IP networks is restricted (SSRF protection)"
                return True, "Valid"

        # Check for invalid TLD or internal host without dot (e.g., http://internal-server)
        if "." not in hostname_lower and not self.allow_localhost:
            return False, "Host must be a valid public FQDN or IP address"

        return True, "Valid"
