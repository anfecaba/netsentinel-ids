"""Extracción de credenciales en texto plano de peticiones HTTP.

Nunca registra ni persiste valores: solo los devuelve al llamador para que
los publique por el WebSocket del laboratorio.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl

from .config import MAX_CREDENTIAL_VALUE, MAX_JSON_DEPTH
from .models import CredentialField, HttpRequest

# Coincidencia exacta (tras normalizar) -> categoría.
_EXACT: Dict[str, str] = {
    "username": "user",
    "user": "user",
    "userid": "user",
    "usuario": "user",
    "login": "user",
    "loginname": "user",
    "nick": "user",
    "nickname": "user",
    "account": "user",
    "cuenta": "user",
    "password": "password",
    "passwd": "password",
    "pwd": "password",
    "pass": "password",
    "contrasena": "password",
    "contrasenia": "password",
    "clave": "password",
    "secret": "password",
    "email": "email",
    "mail": "email",
    "correo": "email",
    "emailaddress": "email",
    "token": "token",
    "accesstoken": "token",
    "refreshtoken": "token",
    "idtoken": "token",
    "sessionid": "token",
    "session": "token",
    "jwt": "token",
    "bearer": "token",
    "apikey": "token",
    "apitoken": "token",
    "authorization": "token",
    "auth": "token",
    "csrftoken": "token",
}

# Contención (el nombre contiene la pista) -> categoría, en orden de prioridad.
_CONTAINS: Tuple[Tuple[str, str], ...] = (
    ("password", "password"),
    ("passwd", "password"),
    ("contrasen", "password"),
    ("contrase", "password"),
    ("clave", "password"),
    ("email", "email"),
    ("correo", "email"),
    ("token", "token"),
    ("sessionid", "token"),
    ("apikey", "token"),
    ("user", "user"),
    ("usuario", "user"),
)

_IGNORED = frozenset(
    {"comments", "comment", "search", "q", "query", "message", "mensaje", "subject"}
)


def _normalize(name: str) -> str:
    cleaned = name.strip().lower()
    for character in ("[", "]", "_", "-", " ", "."):
        cleaned = cleaned.replace(character, "")
    return cleaned


def classify_field(name: str) -> Optional[str]:
    """Devuelve la categoría de un campo o ``None`` si no parece credencial."""

    normalized = _normalize(name)
    if not normalized or normalized in _IGNORED:
        return None

    exact = _EXACT.get(normalized)
    if exact:
        return exact

    for needle, category in _CONTAINS:
        if needle in normalized:
            return category
    return None


def _confidence(name: str, category: str, source: str) -> float:
    if source == "cookie":
        return 0.9
    if _normalize(name) in _EXACT:
        return 0.99
    if category in ("password", "token"):
        return 0.9
    return 0.85


def _make_field(name: str, value: str, source: str) -> Optional[CredentialField]:
    if not isinstance(value, str) or not value:
        return None
    if len(value) > MAX_CREDENTIAL_VALUE:
        return None
    category = classify_field(name)
    if category is None:
        return None
    return CredentialField(
        name=name,
        value=value,
        category=category,
        confidence=_confidence(name, category, source),
    )


def extract_from_form(body: bytes) -> List[CredentialField]:
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - decode con replace no lanza
        return []

    fields: List[CredentialField] = []
    for name, value in parse_qsl(text, keep_blank_values=False):
        field = _make_field(name, value, "form")
        if field:
            fields.append(field)
    return _dedupe(fields)


def _flatten(value: Any, prefix: str, depth: int) -> Iterable[Tuple[str, str]]:
    if depth > MAX_JSON_DEPTH:
        return []
    if isinstance(value, dict):
        items: List[Tuple[str, str]] = []
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_flatten(child, next_prefix, depth + 1))
        return items
    if isinstance(value, list):
        items = []
        for index, child in enumerate(value):
            items.extend(_flatten(child, f"{prefix}[{index}]", depth + 1))
        return items
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, (str, int, float)):
        return [(prefix, str(value))]
    return []


def extract_from_json(body: bytes) -> List[CredentialField]:
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return []

    fields: List[CredentialField] = []
    for path, value in _flatten(payload, "", 0):
        field = _make_field(path, value, "json")
        if field:
            fields.append(field)
    return _dedupe(fields)


def _decode_basic(value: str) -> Optional[str]:
    parts = value.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "basic":
        return None
    try:
        raw = base64.b64decode(parts[1].strip(), validate=True)
    except (binascii.Error, ValueError):
        return None
    return raw.decode("utf-8", errors="replace")


def extract_from_headers(headers: Dict[str, str]) -> List[CredentialField]:
    fields: List[CredentialField] = []

    authorization = headers.get("authorization", "")
    if authorization:
        decoded = _decode_basic(authorization)
        if decoded:
            fields.append(
                CredentialField(
                    name="authorization",
                    value=decoded,
                    category="token",
                    confidence=0.99,
                )
            )
        elif len(authorization) <= MAX_CREDENTIAL_VALUE:
            fields.append(
                CredentialField(
                    name="authorization",
                    value=authorization,
                    category="token",
                    confidence=0.9,
                )
            )

    api_key = headers.get("x-api-key", "")
    if api_key:
        field = _make_field("x-api-key", api_key, "header")
        if field:
            fields.append(field)

    cookie_header = headers.get("cookie", "")
    if cookie_header:
        for chunk in cookie_header.split(";"):
            name, separator, value = chunk.partition("=")
            if not separator:
                continue
            field = _make_field(name.strip(), value.strip(), "cookie")
            if field:
                fields.append(field)

    return _dedupe(fields)


def _dedupe(fields: List[CredentialField]) -> List[CredentialField]:
    seen = set()
    result: List[CredentialField] = []
    for field in fields:
        key = (field.name, field.value)
        if key in seen:
            continue
        seen.add(key)
        result.append(field)
    return result


def extract_credentials(request: HttpRequest) -> List[CredentialField]:
    content_type = request.headers.get("content-type", "").lower()

    fields: List[CredentialField] = []
    if request.body:
        if "json" in content_type:
            fields.extend(extract_from_json(request.body))
        elif "x-www-form-urlencoded" in content_type or not content_type:
            fields.extend(extract_from_form(request.body))
        else:
            # multipart y otros: se intenta form por si acaso, sin inventar.
            fields.extend(extract_from_form(request.body))

    fields.extend(extract_from_headers(request.headers))
    return _dedupe(fields)
