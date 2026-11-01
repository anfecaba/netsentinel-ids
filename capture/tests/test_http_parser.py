from datetime import datetime, timezone

from lab_capture.http_parser import HttpRequestAssembler, parse_http_request

NOW = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def test_parsea_get_simple():
    raw = b"GET /index.html HTTP/1.1\r\nHost: lab.local\r\n\r\n"
    request = parse_http_request(raw, NOW)

    assert request is not None
    assert request.method == "GET"
    assert request.path == "/index.html"
    assert request.host == "lab.local"
    assert request.body == b""
    assert request.raw_bytes == len(raw)


def test_parsea_post_con_body_completo():
    body = b"username=alice&password=123"
    raw = (
        b"POST /login HTTP/1.1\r\n"
        b"Host: lab.local\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: 27\r\n\r\n" + body
    )
    request = parse_http_request(raw, NOW)

    assert request is not None
    assert request.method == "POST"
    assert request.path == "/login"
    assert request.body == body
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"


def test_sin_doble_crlf_devuelve_none():
    assert parse_http_request(b"GET / HTTP/1.1\r\nHost: lab.local\r\n", NOW) is None


def test_content_length_mayor_que_body_devuelve_none():
    raw = (
        b"POST /login HTTP/1.1\r\n"
        b"Host: lab.local\r\n"
        b"Content-Length: 100\r\n\r\n"
        b"username=alice"
    )
    assert parse_http_request(raw, NOW) is None


def test_linea_de_request_invalida_devuelve_none():
    assert parse_http_request(b"NO-ES-HTTP\r\n\r\n", NOW) is None
    assert parse_http_request(b"\x00\x01\x02", NOW) is None


def test_ensamblador_reconstruye_dos_segmentos():
    body = b"username=alice&password=SuperSecret123"
    head = (
        b"POST /login HTTP/1.1\r\n"
        b"Host: lab.local\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n"
    )
    raw = head + body
    split = 40

    assembler = HttpRequestAssembler()
    first = assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1000, raw[:split], NOW)
    assert first == []

    second = assembler.feed(
        "10.0.0.5", 5000, "10.0.0.9", 80, 1000 + split, raw[split:], NOW
    )
    assert len(second) == 1
    assert second[0].body == body
    assert second[0].source_ip == "10.0.0.5"
    assert second[0].destination_port == 80


def test_ensamblador_ignora_retransmisiones():
    raw = b"GET / HTTP/1.1\r\nHost: lab.local\r\n\r\n"
    assembler = HttpRequestAssembler()

    assert len(assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1000, raw, NOW)) == 1
    assert assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1000, raw, NOW) == []


def test_ensamblador_sobrevive_payload_basura():
    assembler = HttpRequestAssembler()
    events = assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1, b"\xff\xfe\x00basura", NOW)
    assert events == []


def test_ensamblador_corta_buffer_desmesurado():
    assembler = HttpRequestAssembler(max_buffer=100)
    payload = b"A" * 64
    assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1, payload, NOW)
    assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 65, payload, NOW)

    assert assembler.dropped_overflows == 1


def test_ensamblador_soporta_pipelining_basico():
    raw = (
        b"GET /a HTTP/1.1\r\nHost: lab.local\r\n\r\n"
        b"GET /b HTTP/1.1\r\nHost: lab.local\r\n\r\n"
    )
    assembler = HttpRequestAssembler()
    requests = assembler.feed("10.0.0.5", 5000, "10.0.0.9", 80, 1, raw, NOW)

    assert [request.path for request in requests] == ["/a", "/b"]
