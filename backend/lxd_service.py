"""Read-only LXD readiness checks through a local Unix socket."""

from typing import Protocol
from urllib.parse import quote

from pylxd import Client
from pylxd.client import get_session_for_url
from pylxd.exceptions import ClientConnectionFailed, LXDAPIException
from requests.exceptions import RequestException

from .config import Settings


class LXDUnavailable(Exception):
    """LXD cannot currently serve this application."""


class ReadinessProbe(Protocol):
    def check_ready(self) -> None: ...


class LXDService:
    def __init__(self, settings: Settings):
        self.endpoint = "http+unix://" + quote(settings.lxd_socket_path, safe="")
        self.timeout = settings.lxd_timeout_seconds

    def check_ready(self) -> None:
        try:
            # A new session gives each request a fresh daemon check and is closed
            # even if Client construction fails. No shared mutable HTTP session.
            with get_session_for_url(self.endpoint) as session:
                session.trust_env = False
                client = Client(
                    endpoint=self.endpoint,
                    timeout=self.timeout,
                    session=session,
                )
                version = client.host_info.get("environment", {}).get("server_version", "")
                if not client.trusted or not version.startswith("5."):
                    raise LXDUnavailable("LXD is unavailable.")
        except (
            ClientConnectionFailed, LXDAPIException, RequestException,
            OSError, ValueError, KeyError, TypeError,
        ) as error:
            raise LXDUnavailable("LXD is unavailable.") from error
