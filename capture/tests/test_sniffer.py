from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, TCP, UDP
from scapy.packet import Raw

from lab_capture.sniffer import CaptureEngine


def _engine():
    events = []
    return CaptureEngine("test0", events.append), events


def _http_post(seq: int = 1000):
    body = b"username=alice&password=SuperSecret123"
    raw = (
        b"POST /login HTTP/1.1\r\n"
        b"Host: lab.local\r\n"
        b"Content-Type: application/x-www-form-urlencoded\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
    )
    return raw, (
        IP(src="192.168.1.23", dst="192.168.1.7")
        / TCP(sport=52301, dport=80, seq=seq, flags="PA")
        / Raw(load=raw)
    )


def test_post_http_emite_flujo_y_credencial():
    engine, events = _engine()
    _, packet = _http_post()
    engine.handle_packet(packet)

    assert [event["type"] for event in events] == ["flow", "credential"]

    flow = events[0]
    assert flow["protocol"] == "HTTP"
    assert flow["encrypted"] is False
    assert flow["riskLevel"] == "danger"
    assert flow["method"] == "POST"
    assert flow["path"] == "/login"
    assert flow["host"] == "lab.local"

    credential = events[1]
    values = {field["name"]: field["value"] for field in credential["fields"]}
    assert values["username"] == "alice"
    assert values["password"] == "SuperSecret123"
    assert credential["flowId"] == flow["id"]
    assert credential["synthetic"] is False


def test_https_solo_emite_metadatos_tls():
    engine, events = _engine()
    packet = (
        IP(src="192.168.1.23", dst="192.168.1.7")
        / TCP(sport=52302, dport=443, seq=2000, flags="PA")
        / Raw(load=b"\x16\x03\x01\x00\x50tls-client-hello")
    )
    engine.handle_packet(packet)

    assert len(events) == 1
    assert events[0]["type"] == "flow"
    assert events[0]["protocol"] == "HTTPS"
    assert events[0]["encrypted"] is True
    assert "TLS" in events[0]["note"]


def test_dns_emite_consulta_y_flujo():
    engine, events = _engine()
    packet = (
        IP(src="192.168.1.23", dst="8.8.8.8")
        / UDP(sport=53000, dport=53)
        / DNS(rd=1, qd=DNSQR(qname="example.com", qtype="A"))
    )
    engine.handle_packet(packet)

    assert [event["type"] for event in events] == ["dns", "flow"]
    assert events[0]["query"] == "example.com"
    assert events[1]["protocol"] == "DNS"
    assert events[1]["host"] == "example.com"


def test_paquete_sin_ip_no_emite_nada():
    engine, events = _engine()
    engine.handle_packet(Raw(load=b"no-ip"))

    assert events == []
    assert engine.packets_seen == 1


def test_body_incompleto_no_emite_credencial():
    engine, events = _engine()
    raw, _ = _http_post()
    truncated = raw[:-10]
    packet = (
        IP(src="192.168.1.23", dst="192.168.1.7")
        / TCP(sport=52303, dport=80, seq=3000, flags="PA")
        / Raw(load=truncated)
    )
    engine.handle_packet(packet)

    assert events == []


def test_http_sin_credenciales_no_emite_credential():
    engine, events = _engine()
    raw = b"GET /index.html HTTP/1.1\r\nHost: lab.local\r\n\r\n"
    packet = (
        IP(src="192.168.1.23", dst="192.168.1.7")
        / TCP(sport=52304, dport=80, seq=4000, flags="PA")
        / Raw(load=raw)
    )
    engine.handle_packet(packet)

    assert [event["type"] for event in events] == ["flow"]
    assert events[0]["riskLevel"] == "warning"


def test_contadores_reflejan_actividad():
    engine, _ = _engine()
    _, packet = _http_post()
    engine.handle_packet(packet)

    assert engine.packets_seen == 1
    assert engine.flows_emitted == 1
    assert engine.credentials_found == 1
