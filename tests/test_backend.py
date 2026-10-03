"""Exercise HTTP failure behavior and configuration boundaries."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from falcon import testing
from requests.exceptions import Timeout

from backend.app import create_app
from backend.config import Settings
from backend.lxd_service import LXDService, LXDUnavailable


class SwitchableProbe:
    error = None
    calls = 0

    def check_ready(self):
        self.calls += 1
        if self.error is not None:
            raise self.error


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.probe = SwitchableProbe()
        self.client = testing.TestClient(create_app(Settings(), self.probe))

    def test_liveness_does_not_contact_unavailable_lxd(self):
        self.probe.error = LXDUnavailable("private daemon details")
        response = self.client.simulate_get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertEqual(self.probe.calls, 0)

    def test_readiness_recovers_without_restarting_api(self):
        self.probe.error = LXDUnavailable("private daemon details")
        response = self.client.simulate_get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"]["code"], "lxd_unavailable")
        self.assertNotIn("private", response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.probe.error = None
        response = self.client.simulate_get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ready"})
        self.assertEqual(self.probe.calls, 2)

    def test_unexpected_error_is_sanitized(self):
        self.probe.error = RuntimeError("secret-token-for-test")
        with self.assertLogs("backend.app", level="ERROR") as logs:
            response = self.client.simulate_get("/ready")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json["error"]["code"], "internal_error")
        self.assertNotIn("secret-token-for-test", response.text + str(logs.output))

    def test_unknown_route_and_wrong_method(self):
        self.assertEqual(self.client.simulate_get("/containers").status_code, 404)
        response = self.client.simulate_post("/health")
        self.assertEqual(response.status_code, 405)
        self.assertIn("GET", response.headers["allow"])
        self.assertIn("error", response.json)


class ConfigurationTests(unittest.TestCase):
    def load_values(self, text, environment=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(text)
            with patch.dict(os.environ, environment or {}, clear=True):
                return Settings.load(path)

    def test_process_environment_overrides_file_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("GOOGLE_CLIENT_SECRET=file-secret\n")
            with patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET": "process-secret"}, clear=True):
                settings = Settings.load(path)
                self.assertEqual(settings.google_client_secret, "process-secret")
                self.assertNotIn("process-secret", repr(settings))
                self.assertNotIn("file-secret", repr(settings))
                self.assertEqual(dict(os.environ), {"GOOGLE_CLIENT_SECRET": "process-secret"})

    def test_bad_timeout_values_are_rejected(self):
        for value in ("0", "-1", "nan", "inf", "31", "invalid"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load_values(f"LXD_TIMEOUT_SECONDS={value}\n")

    def test_local_callback_and_secret_literal(self):
        settings = self.load_values("GOOGLE_CLIENT_SECRET='literal${VALUE}'\n")
        self.assertEqual(settings.google_client_secret, "literal${VALUE}")
        self.assertEqual(settings.google_redirect_uri, "http://localhost:8000/auth/google/callback")

    def test_remote_plain_http_and_relative_socket_are_rejected(self):
        for text in (
            "GOOGLE_REDIRECT_URI=http://example.com/auth/google/callback\n",
            "GOOGLE_REDIRECT_URI=https://example.com:invalid/callback\n",
            "LXD_SOCKET_PATH=relative.socket\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load_values(text)


class LXDServiceTests(unittest.TestCase):
    def test_timeout_is_translated_and_session_closed(self):
        with patch("backend.lxd_service.get_session_for_url") as session_factory:
            with patch("backend.lxd_service.Client", side_effect=Timeout("private details")) as factory:
                with self.assertRaises(LXDUnavailable):
                    LXDService(Settings()).check_ready()
                self.assertEqual(factory.call_args.kwargs["timeout"], 5.0)
            session_factory.return_value.__exit__.assert_called_once()

    def test_untrusted_daemon_is_not_ready(self):
        with patch("backend.lxd_service.get_session_for_url"):
            with patch("backend.lxd_service.Client") as factory:
                factory.return_value.trusted = False
                factory.return_value.host_info = {"environment": {"server_version": "5.21.8"}}
                with self.assertRaises(LXDUnavailable):
                    LXDService(Settings()).check_ready()


if __name__ == "__main__":
    unittest.main()
