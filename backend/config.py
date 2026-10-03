"""Load settings without printing credentials or changing process environment."""

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    google_client_id: str = field(default="", repr=False)
    google_client_secret: str = field(default="", repr=False)
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    bootstrap_admin_email: str = field(default="", repr=False)
    lxd_socket_path: str = "/var/snap/lxd/common/lxd/unix.socket"
    lxd_timeout_seconds: float = 5.0

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        values = dotenv_values(
            env_file if env_file is not None else PROJECT_ROOT / ".env",
            interpolate=False,
        )

        def get(name: str, default: str = "") -> str:
            # Explicit process settings take precedence over the local file.
            return os.environ.get(name, values.get(name) or default).strip()

        try:
            timeout = float(get("LXD_TIMEOUT_SECONDS", "5"))
        except ValueError:
            raise ValueError("LXD_TIMEOUT_SECONDS must be a number between 0 and 30.") from None
        if not math.isfinite(timeout) or not 0 < timeout <= 30:
            raise ValueError("LXD_TIMEOUT_SECONDS must be greater than 0 and at most 30.")

        socket_path = get("LXD_SOCKET_PATH", cls.lxd_socket_path)
        if not Path(socket_path).is_absolute():
            raise ValueError("LXD_SOCKET_PATH must be an absolute Unix socket path.")

        redirect_uri = get("GOOGLE_REDIRECT_URI", cls.google_redirect_uri)
        try:
            parsed = urlsplit(redirect_uri)
            valid_port = parsed.port  # Also reject malformed port numbers.
            del valid_port
            local_http = parsed.scheme == "http" and parsed.hostname in {
                "localhost", "127.0.0.1", "::1",
            }
            valid_redirect = (
                bool(parsed.hostname)
                and (parsed.scheme == "https" or local_http)
                and bool(parsed.path)
                and parsed.username is None
                and parsed.password is None
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid_redirect = False
        if not valid_redirect:
            raise ValueError("GOOGLE_REDIRECT_URI must be an HTTPS callback URL or local HTTP URL.")

        return cls(
            google_client_id=get("GOOGLE_CLIENT_ID"),
            google_client_secret=get("GOOGLE_CLIENT_SECRET"),
            google_redirect_uri=redirect_uri,
            bootstrap_admin_email=get("BOOTSTRAP_ADMIN_EMAIL"),
            lxd_socket_path=socket_path,
            lxd_timeout_seconds=timeout,
        )
