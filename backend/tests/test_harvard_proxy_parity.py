"""
Parity test for the Harvard Proxy module (doc 99, Phase 1).

Verifies the four contract points inherited from proxy/proxy.py without
needing a real Harvard API key: a stub server stands in for Harvard.
"""
import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from fastapi.testclient import TestClient

captured = {}


class StubHarvard(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        captured["path"] = parsed.path
        captured["params"] = parse_qs(parsed.query)

        if parsed.path == "/badjson":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html>not json</html>")
            return

        if parsed.path == "/notfound":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"nope"}')
            return

        body = {
            "info": {"totalrecords": 10, "page": 1, "next": "SHOULD_BE_REMOVED", "prev": "ALSO_REMOVED"},
            "records": [{"id": 299843, "title": "Test Artwork"}],
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 9099), StubHarvard)
threading.Thread(target=server.serve_forever, daemon=True).start()

import os
os.environ["HARVARD_API_KEY"] = "TEST_KEY_123"
os.environ["HARVARD_API_BASE_URL"] = "http://127.0.0.1:9099"

from app.core.config import get_settings
get_settings.cache_clear()
from app.main import app

client = TestClient(app)
failures = []

def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        failures.append(name)

print("\nContract point 1 & 2 - path forwarded, apikey injected server-side")
r = client.get("/proxy/object/299843", params={"size": "10"})
check("200 returned", r.status_code == 200, f"got {r.status_code}")
check("path forwarded verbatim", captured["path"] == "/object/299843", captured.get("path"))
check("client param forwarded", captured["params"].get("size") == ["10"])
check("apikey injected", captured["params"].get("apikey") == ["TEST_KEY_123"])

print("\nContract point 3 - info.next / info.prev stripped")
body = r.json()
check("info.next removed", "next" not in body["info"])
check("info.prev removed", "prev" not in body["info"])
check("other info fields kept", body["info"]["totalrecords"] == 10)
check("records untouched", body["records"][0]["title"] == "Test Artwork")

print("\nContract point 4 - error handling (doc 07 section 3/6)")
r = client.get("/proxy/notfound")
check("non-200 -> 502", r.status_code == 502, f"got {r.status_code}")
check("error code correct", r.json()["error"]["code"] == "HARVARD_API_ERROR")

r = client.get("/proxy/badjson")
check("non-JSON -> 502", r.status_code == 502, f"got {r.status_code}")
check("error code correct", r.json()["error"]["code"] == "HARVARD_API_ERROR")

print("\nKey never leaked to client (RNF-005)")
r = client.get("/proxy/object/299843")
check("key absent from response body", "TEST_KEY_123" not in r.text)

print("\nNested path (proxy/object/{id}/people, used by the detail page)")
client.get("/proxy/object/299843/people")
check("nested path forwarded", captured["path"] == "/object/299843/people", captured.get("path"))

server.shutdown()
print("\n" + ("ALL PASSED" if not failures else f"{len(failures)} FAILURE(S): {failures}"))
raise SystemExit(1 if failures else 0)
