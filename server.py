"""Autonomous synthetic-data demo server for Alfa.Bolshe (no external APIs)."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, unquote

ROOT = Path(__file__).resolve().parent
DB_FILE = Path(os.environ.get("ALFA_DB_PATH", "/data/alfa-bolshe.sqlite"))
PORT = int(os.environ.get("PORT", "8080"))
MAX_REQUEST_BYTES = 300_000
LOCK = threading.RLock()


def inn_is_valid(value: str) -> bool:
    if not value.isdigit() or len(value) not in (10, 12):
        return False
    digits = list(map(int, value))
    check = lambda coefs: sum(a*b for a, b in zip(digits, coefs)) % 11 % 10
    if len(digits) == 10:
        return check([2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[9]
    return (check([7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[10]
            and check([3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == digits[11])


def fact(value, source="Синтетический реестр — демоверсия", period=None):
    obj = {"value": value, "source": source,
           "evidence": "Выдуманные данные для демонстрации. Не ФНС."}
    if period: obj["period"] = period
    return obj


COMPANIES = {
    "0000000000": {"name": fact("ООО «Тестовая кофейня»"), "inn": fact("0000000000"),
        "ogrn": fact("ДЕМО-ОГРН"), "form": fact("ООО"), "status": fact("Действует (демо)"),
        "registered": fact("15.02.2023"), "city": fact("Москва"), "industry": fact("Кофейня и общепит"),
        "okved": fact("56.10"), "workers": fact(8), "revenue": fact(16800000, period="2025"),
        "profit": fact(1800000, period="2025")},
    "000000000000": {"name": fact("ИП Тестовый Предприниматель"), "inn": fact("000000000000"),
        "ogrn": fact("ДЕМО-ОГРНИП"), "form": fact("ИП"), "status": fact("Действует (демо)"),
        "registered": fact("18.03.2024"), "city": fact("Москва"),
        "industry": fact("Дополнительное образование"), "okved": fact("85.41"),
        "workers": fact(5), "revenue": fact(9500000, period="2025")},
}


def connection():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_FILE), timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
    return db


def list_apps():
    with LOCK, connection() as db:
        rows = db.execute("SELECT payload FROM applications ORDER BY updated_at, id").fetchall()
    return [json.loads(row[0]) for row in rows]


def upsert_app(app):
    if not isinstance(app, dict) or not isinstance(app.get("id"), str) or not re.fullmatch(r"[\w.\-]{1,100}", app["id"]):
        raise ValueError("Некорректный идентификатор заявки")
    if not isinstance(app.get("profile"), dict) or not isinstance(app.get("history", []), list):
        raise ValueError("Некорректная структура заявки")
    s = json.dumps(app, ensure_ascii=False, separators=(",", ":"))
    if len(s.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError("Заявка слишком большая")
    with LOCK, connection() as db:
        db.execute("INSERT INTO applications (id, payload, updated_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                   (app["id"], s, datetime.now(timezone.utc).isoformat()))
        db.commit()
    return app["id"]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def respond(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            return self.respond(200, {"status": "ok", "demo": True})
        if url.path == "/api/company":
            inn = parse_qs(url.query).get("inn", [""])[0]
            if not inn_is_valid(inn):
                return self.respond(400, {"error": "Неверный ИНН. Проверьте контрольные цифры."})
            if inn not in COMPANIES:
                return self.respond(404, {"error": "Демонстрационный реестр содержит только синтетические компании с ИНН 0000000000 и 000000000000. Реальная ФНС не подключена. Можно заполнить профиль вручную."})
            return self.respond(200, {"fields": COMPANIES[inn], "synthetic": True})
        if url.path == "/api/applications":
            return self.respond(200, {"applications": list_apps(), "synthetic": True})
        if url.path.startswith("/api/"):
            return self.respond(404, {"error": "Неизвестный API-адрес"})
        segments = [unquote(s) for s in url.path.split("/") if s]
        if any(s.startswith(".") for s in segments) or url.path in ("/server.py", "/Dockerfile", "/compose.yaml", "/openapi.yaml", "/THIRD_PARTY_NOTICES", "/requirements.lock", "/README.md") or url.path.startswith(("/docs/", "/tests/", "/_export/", "/data/")):
            return self.respond(404, {"error": "Ресурс недоступен"})
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/applications":
            return self.respond(404, {"error": "Неизвестный API-адрес"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > MAX_REQUEST_BYTES:
                return self.respond(413, {"error": "Допустимый размер JSON 300 КБ"})
            body = json.loads(self.rfile.read(length))
            app_id = upsert_app(body)
            return self.respond(200, {"ok": True, "id": app_id})
        except (ValueError, json.JSONDecodeError) as e:
            return self.respond(400, {"error": str(e)})

    def end_headers(self):
        if not getattr(self, '_sent_security_headers', False):
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()


if __name__ == "__main__":
    with connection(): pass
    print(f"Alfa.Bolshe DEMO: http://localhost:{PORT} | synthetic data only", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
