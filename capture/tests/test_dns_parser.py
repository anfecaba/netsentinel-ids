from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, TCP, UDP

from lab_capture.dns_parser import QTYPE_NAMES, parse_dns_packet


def _query(qname: str = "example.com", qtype: str = "A") -> object:
    return IP(src="192.168.1.23", dst="8.8.8.8") / UDP(sport=53000, dport=53) / DNS(
        rd=1, qd=DNSQR(qname=qname, qtype=qtype)
    )


def test_parsea_consulta_dns():
    event = parse_dns_packet(_query())

    assert event is not None
    assert event["type"] == "dns"
    assert event["query"] == "example.com"
    assert event["qtype"] == "A"
    assert event["sourceIp"] == "192.168.1.23"
    assert event["destinationIp"] == "8.8.8.8"
    assert event["encrypted"] is False
    assert event["synthetic"] is False


def test_normaliza_punto_final_y_qtype_aaaa():
    event = parse_dns_packet(_query(qname="lab.local.", qtype="AAAA"))

    assert event is not None
    assert event["query"] == "lab.local"
    assert event["qtype"] == "AAAA"


def test_ignora_respuestas_dns():
    packet = (
        IP(src="8.8.8.8", dst="192.168.1.23")
        / UDP(sport=53, dport=53000)
        / DNS(qr=1, qd=DNSQR(qname="example.com", qtype="A"))
    )

    assert parse_dns_packet(packet) is None


def test_ignora_paquetes_sin_dns():
    packet = IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=1234, dport=80)
    assert parse_dns_packet(packet) is None


def test_mapa_de_tipos_conocidos():
    assert QTYPE_NAMES[1] == "A"
    assert QTYPE_NAMES[28] == "AAAA"
    assert QTYPE_NAMES[65] == "HTTPS"
