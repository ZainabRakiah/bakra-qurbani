#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
STORE_PATH = DATA_DIR / "store.json"
UPLOAD_DIR = ROOT / "uploads"
HOST = os.environ.get("BAKRA_HOST", "127.0.0.1")
PORT = int(os.environ.get("BAKRA_PORT", "8000"))

ADMIN_USERNAME = os.environ.get("BAKRA_ADMIN_USERNAME", "BakraSellers")
ADMIN_SALT = b"bakra-bazaar-admin-v1"
ADMIN_PASSWORD_HASH = "VIbN9t9+aI1AeREVEPJ05PnEoJli2fdWpB3zATvkUhU="
SESSION_COOKIE = "bb_session"
SESSION_TTL_SECONDS = 60 * 60 * 8

ORDER_STATUSES = [
    "WhatsApp confirmation pending",
    "Booked",
    "Confirmed",
    "Preparing",
    "Out for delivery",
    "Delivered",
    "Cancelled",
]

SERVICES = {
    "alive": {
        "id": "alive",
        "en": "Delivered Alive to Home",
        "ur": "زندہ گھر پر ڈیلیور",
        "extra": 0,
        "flat_fee": None,
        "available": "15–27 May",
        "note_en": "Open 15–27 May only. Tell us how many kg goat you want; delivery fee is charged separately. Door delivery within 25 km of Munireddy Palya, JC Nagar.",
        "note_ur": "صرف 15 تا 27 مئی کھلا۔ بتا دیں آپ کتنے کلو کا بکرا چاہتے ہیں؛ ڈیلیوری فیس الگ وصول ہوگی۔ Munireddy Palya,\nJC Nagar سے 25 کلومیٹر کے اندر گھر ڈیلیوری۔",
    },
    "cut": {
        "id": "cut",
        "en": "Cut & Delivered to Home",
        "ur": "ذبح کر کے گھر ڈیلیور",
        "extra": 26500,
        "flat_fee": 26500,
        "available": "Eid 28–30 May",
        "note_en": "Fixed price ₹26,500 — not per kg. Minimum 18 kg meat guaranteed on all three Eid days (28–30 May 2026). Free door delivery within 25 km of Munireddy Palya, JC Nagar.",
        "note_ur": "مقررہ قیمت ₹26,500 — فی کلو نہیں۔ عید کے تینوں دنوں (28–30 مئی 2026) کم از کم 18 کلو گوشت کی ضمانت۔ Munireddy Palya,\nJC Nagar سے 25 کلومیٹر کے اندر مفت گھر ڈیلیوری۔",
    },
    "poor": {
        "id": "poor",
        "en": "Cut & Distributed to Poor",
        "ur": "ذبح کر کے غریبوں میں تقسیم",
        "extra": 26500,
        "flat_fee": 26500,
        "available": "Eid 28–30 May",
        "note_en": "Fixed price ₹26,500 — not per kg. Minimum 18 kg meat guaranteed on all three Eid days (28–30 May 2026). Cut and distributed to the poor.",
        "note_ur": "مقررہ قیمت ₹26,500 — فی کلو نہیں۔ عید کے تینوں دنوں (28–30 مئی 2026) کم از کم 18 کلو گوشت کی تقسیم کی ضمانت۔ ذبح کر کے غریبوں میں تقسیم۔",
    },
}

DEFAULT_BREEDS = ["Sirohi", "Beetal", "Jamunapari", "Barbari", "Totapari", "Black Bengal"]

DEFAULT_GOATS = [
    {
        "id": 1,
        "name_en": "Sirohi Brown",
        "name_ur": "سروہی براؤن",
        "breed": "Sirohi",
        "img": "https://novellum-filestore-mcp.s3.us-east-2.amazonaws.com/atxp:atxp_acct_RNctQSbdd3kyQbSrBf4RO/476686ef-e973-4cda-ab0c-81b063cda9e1.png",
        "badge": "Premium",
        "weight": "45 kg",
        "price": 75000,
    },
    {
        "id": 2,
        "name_en": "Royal White Bakra",
        "name_ur": "شاہی سفید بکرا",
        "breed": "Jamunapari",
        "img": "https://novellum-filestore-mcp.s3.us-east-2.amazonaws.com/atxp:atxp_acct_RNctQSbdd3kyQbSrBf4RO/f2edd678-d554-4f02-9f95-fd1ef4bfabb9.png",
        "badge": "Best Seller",
        "weight": "60 kg",
        "price": 95000,
    },
    {
        "id": 3,
        "name_en": "Black Beauty",
        "name_ur": "بلیک بیوٹی",
        "breed": "Black Bengal",
        "img": "https://novellum-filestore-mcp.s3.us-east-2.amazonaws.com/atxp:atxp_acct_RNctQSbdd3kyQbSrBf4RO/470f1b33-059f-4147-9d38-84949560a7e2.png",
        "badge": "New Arrival",
        "weight": "40 kg",
        "price": 55000,
    },
    {
        "id": 4,
        "name_en": "Beetal Champion",
        "name_ur": "بیتل چیمپئن",
        "breed": "Beetal",
        "img": "https://images.unsplash.com/photo-1533318087102-b3ad366ed041?auto=format&fit=crop&w=800&q=80",
        "badge": "Premium",
        "weight": "55 kg",
        "price": 85000,
    },
    {
        "id": 5,
        "name_en": "Barbari Special",
        "name_ur": "بربری اسپیشل",
        "breed": "Barbari",
        "img": "https://images.unsplash.com/photo-1524024973431-2ad916746881?auto=format&fit=crop&w=800&q=80",
        "badge": "Budget",
        "weight": "30 kg",
        "price": 35000,
    },
    {
        "id": 6,
        "name_en": "Totapari Elite",
        "name_ur": "توتاپری ایلیٹ",
        "breed": "Totapari",
        "img": "https://images.unsplash.com/photo-1605000797499-95a51c5269ae?auto=format&fit=crop&w=800&q=80",
        "badge": "Luxury",
        "weight": "70 kg",
        "price": 110000,
    },
]

store_lock = threading.Lock()
sessions: dict[str, dict[str, object]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_store() -> dict[str, object]:
    return {
        "goats": DEFAULT_GOATS,
        "breeds": DEFAULT_BREEDS,
        "orders": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def load_store_unlocked() -> dict[str, object]:
    DATA_DIR.mkdir(exist_ok=True)
    if not STORE_PATH.exists():
        store = default_store()
        save_store_unlocked(store)
        return store

    with STORE_PATH.open("r", encoding="utf-8") as fh:
        store = json.load(fh)

    changed = False
    if "goats" not in store or not isinstance(store["goats"], list):
        store["goats"] = DEFAULT_GOATS
        changed = True
    if "breeds" not in store or not isinstance(store["breeds"], list):
        store["breeds"] = DEFAULT_BREEDS[:]
        changed = True
    if "orders" not in store or not isinstance(store["orders"], list):
        store["orders"] = []
        changed = True

    known_breeds = {clean_text(b) for b in store["breeds"] if clean_text(b)}
    for goat in store["goats"]:
        if "age_en" in goat:
            goat.pop("age_en", None)
            changed = True
        if "age_ur" in goat:
            goat.pop("age_ur", None)
            changed = True
        breed = clean_text(goat.get("breed"))
        if breed and breed not in known_breeds:
            store["breeds"].append(breed)
            known_breeds.add(breed)
            changed = True

    if changed:
        store["updated_at"] = now_iso()
        save_store_unlocked(store)
    return store


def save_store_unlocked(store: dict[str, object]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    store["updated_at"] = now_iso()
    tmp_path = STORE_PATH.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(store, fh, indent=2, ensure_ascii=False)
    os.replace(tmp_path, STORE_PATH)


def check_password(password: str) -> bool:
    expected = base64.b64decode(ADMIN_PASSWORD_HASH)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), ADMIN_SALT, 200_000)
    return hmac.compare_digest(actual, expected)


def clean_text(value: object, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def clean_price(value: object) -> int | None:
    try:
        price = int(value)
    except (TypeError, ValueError):
        return None
    if price < 0 or price > 10_000_000:
        return None
    return price


def clean_breed(value: object) -> str:
    breed = clean_text(value)
    return " ".join(breed.split())


def add_breed_unlocked(store: dict[str, object], breed: str) -> None:
    breed = clean_breed(breed)
    if not breed:
        return
    existing = {str(item).casefold() for item in store.get("breeds", [])}
    if breed.casefold() not in existing:
        store.setdefault("breeds", []).append(breed)


def find_goat(goats: list[dict[str, object]], goat_id: int) -> dict[str, object] | None:
    return next((goat for goat in goats if goat.get("id") == goat_id), None)


def find_order(orders: list[dict[str, object]], order_id: str) -> dict[str, object] | None:
    wanted = order_id.upper()
    return next((order for order in orders if str(order.get("order_id", "")).upper() == wanted), None)


def next_goat_id(goats: list[dict[str, object]]) -> int:
    ids = [int(goat.get("id", 0)) for goat in goats if isinstance(goat.get("id", 0), int)]
    return (max(ids) if ids else 0) + 1


def make_order_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"BB-{stamp}-{secrets.token_hex(3).upper()}"


def order_public(order: dict[str, object]) -> dict[str, object]:
    return {
        "order_id": order.get("order_id"),
        "goat_id": order.get("goat_id"),
        "goat_name": order.get("goat_name"),
        "goat_breed": order.get("goat_breed"),
        "goat_img": order.get("goat_img"),
        "service": order.get("service"),
        "total_price": order.get("total_price"),
        "customer_name": order.get("customer_name"),
        "phone": order.get("phone"),
        "address": order.get("address"),
        "notes": order.get("notes"),
        "status": order.get("status"),
        "history": order.get("history", []),
        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at"),
    }


def _parse_multipart_file(
    content_type: str, body: bytes, field_name: str
) -> tuple[bytes, str, str] | None:
    boundary = None
    for piece in content_type.split(";"):
        piece = piece.strip()
        if piece.startswith("boundary="):
            boundary = piece.split("=", 1)[1].strip().strip('"')
    if not boundary:
        return None

    delimiter = ("--" + boundary).encode()
    for part in body.split(delimiter):
        if b"Content-Disposition" not in part:
            continue
        header_end = part.find(b"\r\n\r\n")
        if header_end < 0:
            continue
        headers = part[:header_end].decode("utf-8", errors="replace")
        if f'name="{field_name}"' not in headers:
            continue
        filename = ""
        mime = ""
        for line in headers.split("\r\n"):
            lower = line.lower()
            if lower.startswith("content-type:"):
                mime = line.split(":", 1)[1].strip()
            if 'filename="' in line:
                filename = line.split('filename="', 1)[1].split('"', 1)[0]
        data = part[header_end + 4 :]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        return data, filename, mime
    return None


class BakraHandler(BaseHTTPRequestHandler):
    server_version = "BakraBazaar/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, status: int, payload: object, extra_headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, object] | None:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            self.send_json(413, {"error": "Request body is too large"})
            return None
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})
            return None

    def read_image_upload(self) -> dict[str, object] | None:
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_json(400, {"error": "Upload must be multipart/form-data"})
            return None
        length = int(self.headers.get("Content-Length", "0"))
        if length > 8_000_000:
            self.send_json(413, {"error": "Image is too large. Use an image under 8 MB."})
            return None

        body = self.rfile.read(length)
        parsed = _parse_multipart_file(content_type, body, "image")
        if parsed is None:
            self.send_json(400, {"error": "Choose an image file"})
            return None
        content, filename, mime = parsed
        if not content:
            self.send_json(400, {"error": "Image file is empty"})
            return None
        if not filename:
            self.send_json(400, {"error": "Choose an image file"})
            return None

        mime = mime or mimetypes.guess_type(filename)[0] or ""
        allowed = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        ext = allowed.get(mime)
        if not ext:
            ext = Path(filename).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                self.send_json(400, {"error": "Upload a JPG, PNG, WEBP, or GIF image"})
                return None
            if ext == ".jpeg":
                ext = ".jpg"

        UPLOAD_DIR.mkdir(exist_ok=True)
        filename = f"goat-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}{ext}"
        destination = UPLOAD_DIR / filename
        destination.write_bytes(content)
        return {"url": f"/uploads/{filename}", "filename": filename}

    def cookie_session_id(self) -> str | None:
        raw_cookie = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie()
        try:
            jar.load(raw_cookie)
        except cookies.CookieError:
            return None
        morsel = jar.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_admin(self) -> dict[str, object] | None:
        sid = self.cookie_session_id()
        if not sid:
            return None
        session = sessions.get(sid)
        if not session:
            return None
        if float(session.get("expires_at", 0)) < time.time():
            sessions.pop(sid, None)
            return None
        session["expires_at"] = time.time() + SESSION_TTL_SECONDS
        return session

    def require_admin(self) -> bool:
        if self.current_admin():
            return True
        self.send_json(401, {"error": "Admin login required"})
        return False

    def set_session_cookie(self, sid: str) -> str:
        return f"{SESSION_COOKIE}={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_TTL_SECONDS}"

    def clear_session_cookie(self) -> str:
        return f"{SESSION_COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/goats":
            with store_lock:
                store = load_store_unlocked()
                goats = store["goats"]
                breeds = store["breeds"]
            self.send_json(200, {"goats": goats, "breeds": breeds, "services": list(SERVICES.values())})
            return

        if path.startswith("/api/orders/"):
            order_id = path.removeprefix("/api/orders/").strip("/")
            with store_lock:
                store = load_store_unlocked()
                order = find_order(store["orders"], order_id)
            if not order:
                self.send_json(404, {"error": "Order not found"})
                return
            self.send_json(200, {"order": order_public(order)})
            return

        if path == "/api/admin/session":
            session = self.current_admin()
            self.send_json(200, {"authenticated": bool(session), "username": session.get("username") if session else None})
            return

        if path == "/api/admin/orders":
            if not self.require_admin():
                return
            with store_lock:
                store = load_store_unlocked()
                orders = list(reversed(store["orders"]))
            self.send_json(200, {"orders": orders, "statuses": ORDER_STATUSES})
            return

        self.serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/admin/uploads":
            if not self.require_admin():
                return
            upload = self.read_image_upload()
            if upload is not None:
                self.send_json(201, upload)
            return

        body = self.read_json()
        if body is None:
            return

        if path == "/api/admin/login":
            username = clean_text(body.get("username"))
            password = clean_text(body.get("password"))
            if hmac.compare_digest(username, ADMIN_USERNAME) and check_password(password):
                sid = secrets.token_urlsafe(32)
                sessions[sid] = {"username": ADMIN_USERNAME, "expires_at": time.time() + SESSION_TTL_SECONDS}
                self.send_json(200, {"ok": True, "username": ADMIN_USERNAME}, {"Set-Cookie": self.set_session_cookie(sid)})
                return
            self.send_json(401, {"error": "Invalid username or password"})
            return

        if path == "/api/admin/logout":
            sid = self.cookie_session_id()
            if sid:
                sessions.pop(sid, None)
            self.send_json(200, {"ok": True}, {"Set-Cookie": self.clear_session_cookie()})
            return

        if path == "/api/orders":
            self.create_order(body)
            return

        if path == "/api/admin/goats":
            if not self.require_admin():
                return
            self.create_goat(body)
            return

        if path == "/api/admin/breeds":
            if not self.require_admin():
                return
            self.create_breed(body)
            return

        self.send_json(404, {"error": "Route not found"})

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        body = self.read_json()
        if body is None:
            return
        if not self.require_admin():
            return

        if path.startswith("/api/admin/goats/"):
            goat_id_raw = path.removeprefix("/api/admin/goats/").strip("/")
            try:
                goat_id = int(goat_id_raw)
            except ValueError:
                self.send_json(400, {"error": "Invalid goat id"})
                return
            self.update_goat(goat_id, body)
            return

        if path.startswith("/api/admin/orders/"):
            order_id = path.removeprefix("/api/admin/orders/").strip("/")
            self.update_order(order_id, body)
            return

        self.send_json(404, {"error": "Route not found"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if not self.require_admin():
            return

        if path.startswith("/api/admin/goats/"):
            goat_id_raw = path.removeprefix("/api/admin/goats/").strip("/")
            try:
                goat_id = int(goat_id_raw)
            except ValueError:
                self.send_json(400, {"error": "Invalid goat id"})
                return
            with store_lock:
                store = load_store_unlocked()
                before = len(store["goats"])
                store["goats"] = [goat for goat in store["goats"] if goat.get("id") != goat_id]
                if len(store["goats"]) == before:
                    self.send_json(404, {"error": "Goat not found"})
                    return
                save_store_unlocked(store)
            self.send_json(200, {"ok": True})
            return

        if path.startswith("/api/admin/breeds/"):
            breed = clean_breed(path.removeprefix("/api/admin/breeds/").strip("/"))
            if not breed:
                self.send_json(400, {"error": "Invalid breed"})
                return
            with store_lock:
                store = load_store_unlocked()
                in_use = any(str(goat.get("breed", "")).casefold() == breed.casefold() for goat in store["goats"])
                if in_use:
                    self.send_json(409, {"error": "This breed is used by goats. Move those goats first."})
                    return
                before = len(store["breeds"])
                store["breeds"] = [item for item in store["breeds"] if str(item).casefold() != breed.casefold()]
                if len(store["breeds"]) == before:
                    self.send_json(404, {"error": "Breed not found"})
                    return
                save_store_unlocked(store)
            self.send_json(200, {"ok": True})
            return

        self.send_json(404, {"error": "Route not found"})

    def create_order(self, body: dict[str, object]) -> None:
        goat_id = clean_price(body.get("goatId"))
        service_id = clean_text(body.get("serviceId"), "alive")
        customer_name = clean_text(body.get("customerName"))
        phone = clean_text(body.get("phone"))
        address = clean_text(body.get("address"))
        notes = clean_text(body.get("notes"))

        if not goat_id or service_id not in SERVICES:
            self.send_json(400, {"error": "Choose a valid goat and service"})
            return
        if not customer_name or not phone:
            self.send_json(400, {"error": "Customer name and phone are required"})
            return

        with store_lock:
            store = load_store_unlocked()
            goat = find_goat(store["goats"], goat_id)
            if not goat:
                self.send_json(404, {"error": "Goat not found"})
                return
            service = SERVICES[service_id]
            flat_fee = service.get("flat_fee")
            if flat_fee is not None:
                total_price = int(flat_fee)
                base_price = 0
            else:
                base_price = int(goat["price"])
                total_price = base_price + int(service.get("extra") or 0)
            created_at = now_iso()
            order = {
                "order_id": make_order_id(),
                "goat_id": goat["id"],
                "goat_name": goat["name_en"],
                "goat_name_ur": goat.get("name_ur", goat["name_en"]),
                "goat_breed": goat["breed"],
                "goat_img": goat.get("img", ""),
                "service": service,
                "base_price": base_price,
                "total_price": total_price,
                "customer_name": customer_name,
                "phone": phone,
                "address": address,
                "notes": notes,
                "status": "WhatsApp confirmation pending",
                "history": [
                    {
                        "status": "WhatsApp confirmation pending",
                        "note": "Order saved. Please confirm on WhatsApp: Maulana Munavvar Husain Rashadi +91 99867 64178 or Hafiz Riyaz Maseehi +91 99806 06870.",
                        "at": created_at,
                    }
                ],
                "created_at": created_at,
                "updated_at": created_at,
            }
            store["orders"].append(order)
            save_store_unlocked(store)

        self.send_json(201, {"order": order_public(order)})

    def create_goat(self, body: dict[str, object]) -> None:
        name_en = clean_text(body.get("name_en"))
        name_ur = clean_text(body.get("name_ur"), name_en)
        breed = clean_breed(body.get("breed"))
        price = clean_price(body.get("price"))
        weight = clean_text(body.get("weight"))
        img = clean_text(body.get("img"), "https://placehold.co/800x520/0d7c3f/fff?text=Bakra+Bazaar")
        badge = clean_text(body.get("badge"))

        if not all([name_en, breed, price is not None, weight]):
            self.send_json(400, {"error": "Name, breed, price, and weight are required"})
            return

        with store_lock:
            store = load_store_unlocked()
            add_breed_unlocked(store, breed)
            goat = {
                "id": next_goat_id(store["goats"]),
                "name_en": name_en,
                "name_ur": name_ur,
                "breed": breed,
                "img": img,
                "badge": badge,
                "weight": weight,
                "price": price,
            }
            store["goats"].append(goat)
            save_store_unlocked(store)
        self.send_json(201, {"goat": goat})

    def update_goat(self, goat_id: int, body: dict[str, object]) -> None:
        allowed_text = {"name_en", "name_ur", "img", "badge", "weight"}
        with store_lock:
            store = load_store_unlocked()
            goat = find_goat(store["goats"], goat_id)
            if not goat:
                self.send_json(404, {"error": "Goat not found"})
                return
            for field in allowed_text:
                if field in body:
                    goat[field] = clean_text(body.get(field))
            if "breed" in body:
                breed = clean_breed(body.get("breed"))
                if not breed:
                    self.send_json(400, {"error": "Breed is required"})
                    return
                goat["breed"] = breed
                add_breed_unlocked(store, breed)
            if "price" in body:
                price = clean_price(body.get("price"))
                if price is None:
                    self.send_json(400, {"error": "Invalid price"})
                    return
                goat["price"] = price
            save_store_unlocked(store)
        self.send_json(200, {"goat": goat})

    def create_breed(self, body: dict[str, object]) -> None:
        breed = clean_breed(body.get("breed"))
        if not breed:
            self.send_json(400, {"error": "Breed name is required"})
            return
        if len(breed) > 60:
            self.send_json(400, {"error": "Breed name is too long"})
            return
        with store_lock:
            store = load_store_unlocked()
            add_breed_unlocked(store, breed)
            save_store_unlocked(store)
        self.send_json(201, {"breed": breed})

    def update_order(self, order_id: str, body: dict[str, object]) -> None:
        status = clean_text(body.get("status"))
        note = clean_text(body.get("note"))
        if status not in ORDER_STATUSES:
            self.send_json(400, {"error": "Invalid order status"})
            return

        with store_lock:
            store = load_store_unlocked()
            order = find_order(store["orders"], order_id)
            if not order:
                self.send_json(404, {"error": "Order not found"})
                return
            order["status"] = status
            order["updated_at"] = now_iso()
            order.setdefault("history", []).append({"status": status, "note": note, "at": order["updated_at"]})
            save_store_unlocked(store)
        self.send_json(200, {"order": order})

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            file_path = ROOT / "index.html"
        else:
            file_path = (ROOT / path.lstrip("/")).resolve()
            if ROOT not in file_path.parents and file_path != ROOT:
                self.send_error(403)
                return

        if not file_path.exists() or file_path.is_dir():
            file_path = ROOT / "index.html"

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    with store_lock:
        load_store_unlocked()
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), BakraHandler)
    except OSError as exc:
        if exc.errno in {48, 98}:  # macOS / Linux: address already in use
            print(f"Port {PORT} is already in use.")
            print(f"If Bakra Bazaar is already running, open http://{HOST}:{PORT}")
            print(f"To stop the old server: lsof -ti :{PORT} | xargs kill")
            print(f"Or start on another port: BAKRA_PORT=8001 python3 server.py")
            raise SystemExit(1) from exc
        raise
    print(f"Bakra Bazaar running at http://{HOST}:{PORT}")
    print(f"Admin username: {ADMIN_USERNAME}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
