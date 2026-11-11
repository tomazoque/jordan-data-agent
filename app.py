"""Sirve el prototipo local. Ejecuta python app.py --help para ver las opciones."""

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError

from agente import Agent, load_games


WEB = Path(__file__).with_name("web")
FILES = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
}


def serve(agent, port):
    class Handler(BaseHTTPRequestHandler):
        def send(self, body, kind, status=HTTPStatus.OK):
            self.send_response(status)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, payload, status=HTTPStatus.OK):
            self.send(json.dumps(payload, ensure_ascii=False).encode(), "application/json", status)

        def do_GET(self):
            if self.path == "/api/estado":
                self.send_json({"modo": "llama.cpp" if agent.model else "Reglas locales",
                                "modelo": agent.model})
            elif self.path in FILES:
                name, kind = FILES[self.path]
                self.send((WEB / name).read_bytes(), kind)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            if self.path != "/api/consulta":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("Envía una consulta de hasta 500 caracteres.")
                payload = json.loads(self.rfile.read(size))
                question = payload.get("pregunta") if isinstance(payload, dict) else None
                if not isinstance(question, str) or not 0 < len(question.strip()) <= 500:
                    raise ValueError("Escribe una pregunta de hasta 500 caracteres.")
                result = agent.answer(question.strip(), payload.get("anterior"))
            except (URLError, TimeoutError):
                self.send_json({"error": "El modelo local no respondió. Revisa que llama-server esté activo en el puerto 8081."},
                               HTTPStatus.BAD_GATEWAY)
                return
            except (ValueError, KeyError, IndexError, TypeError) as error:
                detail = str(error) if type(error) is ValueError else "La consulta no se pudo interpretar."
                self.send_json({"error": detail}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            self.send_json(result)

    with ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Abre http://127.0.0.1:{port} para explorar los datos.", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", type=int, default=8765)
    parser.add_argument("--modelo", help="Alias del modelo activo en llama-server (puerto 8081)")
    options = parser.parse_args()
    try:
        serve(Agent(load_games(), options.modelo), options.puerto)
    except KeyboardInterrupt:
        pass
