"""Falcon application factory and public diagnostic resources."""

import logging

import falcon

from .config import Settings
from .lxd_service import LXDService, LXDUnavailable, ReadinessProbe


LOGGER = logging.getLogger(__name__)


class HealthResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.media = {"status": "ok"}
        resp.set_header("Cache-Control", "no-store")


class ReadyResource:
    def __init__(self, lxd: ReadinessProbe):
        self.lxd = lxd

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.set_header("Cache-Control", "no-store")
        self.lxd.check_ready()
        resp.media = {"status": "ready"}


def handle_lxd_unavailable(req, resp, error, params):
    resp.status = falcon.HTTP_503
    resp.media = {"error": {"code": "lxd_unavailable", "message": "LXD is unavailable."}}
    resp.set_header("Retry-After", "5")
    resp.set_header("Cache-Control", "no-store")


def serialize_http_error(req, resp, error):
    # Falcon retains the error's status and headers (for example, Allow on 405).
    resp.media = {"error": {"code": "http_error", "message": error.title}}


def handle_unexpected_error(req, resp, error, params):
    # Avoid logging raw exception text, which could contain future credentials.
    LOGGER.error("Unhandled API exception of type %s", type(error).__name__)
    resp.status = falcon.HTTP_500
    resp.media = {"error": {"code": "internal_error", "message": "An internal error occurred."}}
    resp.set_header("Cache-Control", "no-store")


def create_app(
    settings: Settings | None = None,
    lxd_service: ReadinessProbe | None = None,
) -> falcon.App:
    settings = settings if settings is not None else Settings.load()
    lxd = lxd_service if lxd_service is not None else LXDService(settings)
    app = falcon.App()
    app.add_error_handler(Exception, handle_unexpected_error)
    app.add_error_handler(LXDUnavailable, handle_lxd_unavailable)
    app.set_error_serializer(serialize_http_error)
    app.add_route("/health", HealthResource())
    app.add_route("/ready", ReadyResource(lxd))
    return app
