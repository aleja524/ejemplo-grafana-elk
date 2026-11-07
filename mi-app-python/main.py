import datetime
import json
import logging
import socket

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

NOMBRE_APP = "mi-app-python"


class LogstashTCPHandler(logging.Handler):
    """Envía cada log como un JSON por línea a Logstash (TCP)."""

    def __init__(self, host="localhost", port=5001, application=NOMBRE_APP):
        super().__init__()
        self.host = host
        self.port = port
        self.application = application
        self.sock = None

    def _conectar(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=2)

    def emit(self, record):
        evento = {
            "@timestamp": datetime.datetime.fromtimestamp(
                record.created, datetime.timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "application": self.application,
        }
        datos = (json.dumps(evento) + "\n").encode("utf-8")
        for _ in range(2):
            try:
                if self.sock is None:
                    self._conectar()
                self.sock.sendall(datos)
                return
            except OSError:
                self.sock = None
        # Si Logstash no está disponible, la app sigue funcionando.


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(NOMBRE_APP)
logger.setLevel(logging.INFO)
logger.addHandler(LogstashTCPHandler())

app = FastAPI(title=NOMBRE_APP)

# Expone las métricas en formato Prometheus en /metrics
Instrumentator().instrument(app).expose(app)


@app.get("/api/hola")
def hola():
    logger.info("Hola desde mi-app-python")
    return {"mensaje": "Hola"}


@app.get("/api/error")
def error():
    logger.error("Ocurrió un error simulado en mi-app-python")
    return {"mensaje": "Error simulado"}