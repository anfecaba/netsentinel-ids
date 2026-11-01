from datetime import datetime, timezone

from lab_capture.credentials import (
    classify_field,
    extract_credentials,
    extract_from_form,
    extract_from_headers,
    extract_from_json,
)
from lab_capture.models import HttpRequest

NOW = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def test_clasifica_nombres_de_usuario():
    for name in ("username", "user", "usuario", "login", "user_id"):
        assert classify_field(name) == "user", name


def test_clasifica_contrasenas_incluyendo_espanol():
    for name in ("password", "passwd", "pwd", "contrasena", "contraseña", "clave"):
        assert classify_field(name) == "password", name


def test_clasifica_correo_y_tokens():
    for name in ("email", "correo", "mail"):
        assert classify_field(name) == "email", name
    for name in ("token", "access_token", "sessionid", "jwt", "api_key"):
        assert classify_field(name) == "token", name


def test_ignora_campos_que_no_son_credenciales():
    for name in ("comments", "search", "q", "subject"):
        assert classify_field(name) is None, name


def test_extrae_tres_campos_de_formulario():
    fields = extract_from_form(b"username=alice&password=SuperSecret123&email=alice%40lab.local")

    assert [(field.name, field.value, field.category) for field in fields] == [
        ("username", "alice", "user"),
        ("password", "SuperSecret123", "password"),
        ("email", "alice@lab.local", "email"),
    ]


def test_extrae_json_anidado_y_aplanado():
    body = b'{"user":{"name":"alice"},"auth":{"password":"SuperSecret123"}}'
    fields = extract_from_json(body)

    values = {field.name: field.value for field in fields}
    assert len(fields) == 2
    assert "user.name" in values
    assert "auth.password" in values
    assert values["auth.password"] == "SuperSecret123"


def test_decodifica_basic_auth():
    headers = {"authorization": "Basic YWxpY2U6U3VwZXJTZWNyZXQxMjM="}
    fields = extract_from_headers(headers)

    assert len(fields) == 1
    assert fields[0].name == "authorization"
    assert fields[0].value == "alice:SuperSecret123"
    assert fields[0].confidence >= 0.99


def test_extrae_solo_la_cookie_de_sesion():
    headers = {"cookie": "sessionid=abc123; theme=dark"}
    fields = extract_from_headers(headers)

    assert [field.name for field in fields] == ["sessionid"]
    assert fields[0].confidence == 0.9


def test_omite_valores_vacios_o_largos():
    fields = extract_from_form(b"username=&password=" + b"A" * 600)

    assert fields == []


def test_extract_credentials_combina_formulario_y_cabeceras():
    request = HttpRequest(
        method="POST",
        path="/login",
        host="lab.local",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "authorization": "Basic YWxpY2U6U3VwZXJTZWNyZXQxMjM=",
        },
        body=b"username=alice&password=SuperSecret123",
        captured_at=NOW,
        source_ip="10.0.0.5",
        destination_ip="10.0.0.9",
    )

    names = [field.name for field in extract_credentials(request)]
    assert names == ["username", "password", "authorization"]


def test_extract_credentials_no_duplica_campos_iguales():
    request = HttpRequest(
        method="POST",
        path="/login",
        host="lab.local",
        headers={"content-type": "application/x-www-form-urlencoded"},
        body=b"password=SuperSecret123&password=SuperSecret123",
        captured_at=NOW,
        source_ip="10.0.0.5",
        destination_ip="10.0.0.9",
    )

    assert len(extract_credentials(request)) == 1
