"""Signaux de production : éteints sans réglages, et sans rien changer aux réponses.

Les trois réglages POSTHOG_* vont ensemble : aucun, et PostHog reste éteint ;
certains seulement, et le service refuse de démarrer. Allumés, ils envoient
l'exception d'une requête au nom de l'utilisateur connecté, sans que la réponse
change. Un faux hôte PostHog local reçoit ce qui est envoyé.
"""

import gzip
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from types import SimpleNamespace

import pytest
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from requests.exceptions import ConnectionError as RequestsConnectionError

from oceens import summaries_generator_daemon as daemon
from oceens.core import auth, production_signals
from oceens.core.database import create_db_and_tables
from oceens.main import create_app

EMAIL = "oceens.facilitator@epf.fr"


class _PostHogStub(BaseHTTPRequestHandler):
    """Garde les événements reçus, comme l'hôte d'ingestion de PostHog."""

    events = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        # Les logs arrivent en OTLP (protobuf) sur /i/v1/logs : acceptés, ignorés.
        if not self.path.startswith("/i/v1/logs"):
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            self.events.extend(json.loads(body).get("batch", []))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


@pytest.fixture(autouse=True)
def settings_unset(monkeypatch):
    """Chaque test part sans réglage, et finit avec les signaux arrêtés."""
    for name in production_signals.SETTINGS:
        monkeypatch.delenv(name, raising=False)
    yield
    production_signals.stop()


@pytest.fixture
def posthog_host():
    _PostHogStub.events = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _PostHogStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    # La file se vide vers ce faux hôte avant qu'il ne s'arrête.
    production_signals.stop()
    server.shutdown()
    server.server_close()


def start_signals(monkeypatch, host):
    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", host)
    monkeypatch.setenv("POSTHOG_ENVIRONMENT", "test")
    return production_signals.start("oceens")


def exceptions_sent():
    """Les exceptions reçues par le faux hôte, une fois la file vidée."""
    production_signals.stop()
    return [e for e in _PostHogStub.events if e["event"] == "$exception"]


@pytest.fixture
def browser(monkeypatch):
    """L'application, avec deux routes en plus, et un utilisateur connecté.

    Le lifespan ne tourne pas : chaque test démarre ses signaux lui-même.
    """
    monkeypatch.setattr(auth, "DEV_LOGIN_KEY", None)
    create_db_and_tables()
    app = create_app()

    @app.get("/test/raises")
    def raises():
        raise RuntimeError("route qui lève")

    @app.get("/test/catches", response_class=PlainTextResponse)
    def catches():
        try:
            raise RuntimeError("route qui rattrape")
        except RuntimeError as error:
            production_signals.report_caught_exception(error)
            return "réponse de repli"

    client = TestClient(app, raise_server_exceptions=False)
    signed_in = client.post("/dev/login", data={"email": EMAIL}, follow_redirects=False)
    assert signed_in.status_code == 303
    return client


def test_without_settings_nothing_starts():
    assert production_signals.start("oceens") is None
    assert production_signals.client() is None


@pytest.mark.parametrize("missing", production_signals.SETTINGS)
def test_with_only_some_settings_the_service_refuses_to_start(monkeypatch, missing):
    for name in production_signals.SETTINGS:
        if name != missing:
            monkeypatch.setenv(name, "x")

    with pytest.raises(ValueError, match=f"{missing} missing"):
        production_signals.start("oceens")


def test_a_route_that_raises_answers_the_same_500_with_signals_off_or_on(
    monkeypatch, browser, posthog_host
):
    off = browser.get("/test/raises")
    start_signals(monkeypatch, posthog_host)
    on = browser.get("/test/raises")

    assert (off.status_code, off.text) == (500, "Internal Server Error")
    assert (on.status_code, on.text) == (off.status_code, off.text)


def test_with_signals_off_nothing_is_sent(browser, posthog_host):
    browser.get("/test/raises")
    browser.get("/test/catches")

    assert exceptions_sent() == []


def test_an_exception_leaving_a_request_is_sent_with_the_users_email(
    monkeypatch, browser, posthog_host
):
    start_signals(monkeypatch, posthog_host)

    browser.get("/test/raises")

    [sent] = exceptions_sent()
    assert sent["distinct_id"] == EMAIL
    assert sent["properties"]["environment"] == "test"
    assert sent["properties"]["$exception_list"][0]["type"] == "RuntimeError"


def test_a_caught_exception_is_sent_with_the_users_email_and_the_same_answer(
    monkeypatch, browser, posthog_host
):
    off = browser.get("/test/catches")
    start_signals(monkeypatch, posthog_host)
    on = browser.get("/test/catches")

    assert (on.status_code, on.text) == (off.status_code, off.text) == (200, "réponse de repli")
    [sent] = exceptions_sent()
    assert sent["distinct_id"] == EMAIL


def summary_whose_model_check_fails(monkeypatch):
    """Traite une synthèse dont la vérification du modèle lève, comme le daemon.

    Retourne ce que le daemon a écrit sur la ligne : (statut, metadata_text).
    """

    def check_model_fails(provider, model, session):
        raise RequestsConnectionError("fournisseur injoignable")

    finished = []
    monkeypatch.setattr(daemon, "check_model", check_model_fails)
    monkeypatch.setattr(
        daemon,
        "get_provider",
        lambda session, prompt: SimpleNamespace(provider_id=1, name="P", default_model="m"),
    )
    monkeypatch.setattr(
        daemon,
        "finish_summary",
        lambda session, row, status, metadata_text=None, **kw: finished.append(
            (status, metadata_text)
        ),
    )
    session = SimpleNamespace(get=lambda model, key: SimpleNamespace(provider_id=None, model="m"))
    row = SimpleNamespace(summary_id=7, prompt_id=1, survey_id=42)

    with production_signals.context(identity="oceens-summaries"):
        with production_signals.context(survey_id=row.survey_id):
            daemon.process_summary(session, row, None, None, {})

    return finished


def test_a_caught_model_check_failure_is_sent_as_the_daemon_with_its_survey(
    monkeypatch, posthog_host
):
    off = summary_whose_model_check_fails(monkeypatch)
    start_signals(monkeypatch, posthog_host)
    on = summary_whose_model_check_fails(monkeypatch)

    assert on == off == [(daemon.STATUS_CONFIG_ERROR, "fournisseur injoignable")]
    [sent] = exceptions_sent()
    assert sent["distinct_id"] == "oceens-summaries"
    assert sent["properties"]["survey_id"] == 42
    assert sent["properties"]["$exception_list"][0]["type"] == "ConnectionError"


def test_the_log_handler_goes_on_the_root_and_on_loggers_that_do_not_propagate(
    monkeypatch, posthog_host
):
    monkeypatch.setattr(logging.getLogger("uvicorn"), "propagate", False)
    monkeypatch.setattr(logging.getLogger("uvicorn.error"), "propagate", True)
    monkeypatch.setenv("POSTHOG_PROJECT_TOKEN", "phc_test")
    monkeypatch.setenv("POSTHOG_HOST", posthog_host)
    monkeypatch.setenv("POSTHOG_ENVIRONMENT", "test")

    production_signals.start("oceens", logger_names=("uvicorn", "uvicorn.error"))

    def has_handler(name):
        return any(
            type(h).__name__ == "LoggingHandler" for h in logging.getLogger(name).handlers
        )

    assert [has_handler(n) for n in ("", "uvicorn", "uvicorn.error")] == [True, True, False]
    production_signals.stop()
    assert [has_handler(n) for n in ("", "uvicorn", "uvicorn.error")] == [False, False, False]
