"""Signaux de production : erreurs, identité et logs envoyés à PostHog.

Désactivés tant qu'aucun des trois réglages n'est défini : le service tourne
alors exactement comme avant. Définis tous les trois, chaque processus qui
appelle `start()` (le serveur web dans son lifespan, le daemon de synthèses
dans son `main()`) envoie à PostHog :

- ses exceptions (Error tracking), avec la propriété `environment` ;
- l'identité du contexte qui les a levées (`context()`) : l'e-mail de
  l'utilisateur connecté, ou `oceens-summaries` pour le daemon ;
- ses logs (Logs), en OTLP, avec `service.name` et `deployment.environment`.

Une exception que le code rattrape pour répondre lui-même ne sort jamais du
contexte : elle n'est envoyée que si le code la passe à
`report_caught_exception()`.
"""

from contextlib import contextmanager
import logging
import os

import posthog
from posthog import Posthog

# Chemins privés d'OpenTelemetry : l'API des logs n'a pas encore d'équivalent
# public. LoggingHandler émet un DeprecationWarning, attendu lui aussi.
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

# Les trois, ou aucun.
SETTINGS = ("POSTHOG_PROJECT_TOKEN", "POSTHOG_HOST", "POSTHOG_ENVIRONMENT")

# Posés par `start()`, remis à zéro par `stop()`. Un par processus.
_client = None
_log_provider = None
_log_handler = None
_loggers_with_handler = []


def read_settings():
    """Retourne les trois réglages, ou None si aucun n'est défini.

    Lève ValueError en nommant le premier qui manque quand certains seulement
    le sont : un environnement à moitié réglé refuse de démarrer, plutôt que
    de tourner sans rien envoyer.
    """
    values = {name: os.environ.get(name, "").strip() for name in SETTINGS}
    if not any(values.values()):
        return None
    for name, value in values.items():
        if not value:
            raise ValueError(f"{name} missing")
    return values


def start(service_name, logger_names=()):
    """Démarre les signaux de production de ce processus, si réglés.

    `logger_names` : les loggers qu'utilise le code. Le handler des logs va sur
    la racine, et sur ceux d'entre eux qui ne propagent pas vers elle (dans le
    serveur web, `uvicorn`) : sur aucun autre, pour n'envoyer aucune ligne deux
    fois. Retourne le client PostHog, ou None quand les réglages sont absents.
    """
    global _client, _log_provider, _log_handler

    settings = read_settings()
    if settings is None:
        return None

    token = settings["POSTHOG_PROJECT_TOKEN"]
    host = settings["POSTHOG_HOST"].rstrip("/")
    environment = settings["POSTHOG_ENVIRONMENT"]

    _client = Posthog(
        token,
        host=host,
        enable_exception_autocapture=True,
        super_properties={"environment": environment},
    )

    _log_provider = LoggerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "deployment.environment": environment,
            }
        )
    )
    _log_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(
                endpoint=f"{host}/i/v1/logs",
                headers={"Authorization": f"Bearer {token}"},
            )
        )
    )
    _log_handler = LoggingHandler(logger_provider=_log_provider)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    _loggers_with_handler.append(root)
    for name in logger_names:
        named = logging.getLogger(name)
        if not named.propagate:
            _loggers_with_handler.append(named)
    for target in _loggers_with_handler:
        target.addHandler(_log_handler)

    return _client


def stop():
    """Envoie ce qui reste en file, puis arrête le client et les logs."""
    global _client, _log_provider, _log_handler

    for target in _loggers_with_handler:
        target.removeHandler(_log_handler)
    _loggers_with_handler.clear()
    if _client is not None:
        _client.shutdown()
    if _log_provider is not None:
        _log_provider.shutdown()
    _client = None
    _log_provider = None
    _log_handler = None


def client():
    """Le client PostHog de ce processus, ou None quand les signaux sont éteints."""
    return _client


@contextmanager
def context(identity=None, **tags):
    """Ouvre un contexte PostHog, hérité du contexte courant.

    Une exception qui en sort est envoyée, avec `identity` comme utilisateur et
    `tags` comme propriétés, puis relevée telle quelle. Sans signaux, ne fait
    rien : jamais de client global.
    """
    if _client is None:
        yield
        return

    with posthog.new_context(client=_client):
        if identity:
            posthog.identify_context(identity)
        for name, value in tags.items():
            posthog.tag(name, value)
        yield


def report_caught_exception(exception):
    """Envoie une exception que le code rattrape pour répondre lui-même.

    À appeler avant de répondre, dans le contexte de la requête : l'envoi en
    porte l'identité. La réponse ne change pas. Sans signaux, n'envoie rien.
    """
    if _client is not None:
        _client.capture_exception(exception)
