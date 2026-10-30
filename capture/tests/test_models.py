from datetime import datetime, timezone
import json

import pytest

from lab_capture.models import (
    CredentialField,
    iso_utc,
    make_credential_event,
    make_dns_event,
    make_error_event,
    make_flow_event,
    make_hello_event,
    make_stats_event,
)


def test_iso_utc_termina_en_z_y_es_parseable():
    value = iso_utc(datetime(2026, 10, 29, 12, 34, 56, tzinfo=timezone.utc))
    assert value.endswith("Z")
    assert datetime.fromisoformat(value.replace("Z", "+00:00")).year == 2026


def test_make_flow_event_tiene_claves_camel_case():
    event = make_flow_event(
        source_ip="192.168.1.23",
        source_port=52301,
        destination_ip="192.168.1.7",
        destination_port=80,
        protocol="HTTP",
        encrypted=False,
        bytes_transferred=420,
        risk_level="danger",
        host="lab.local",
        method="POST",
        path="/login",
        note="POST sin TLS",
    )

    assert event["type"] == "flow"
    assert event["capturedAt"].endswith("Z")
    assert event["sourceIp"] == "192.168.1.23"
    assert event["destinationPort"] == 80
    assert event["synthetic"] is False
    assert "source_ip" not in event
    json.dumps(event)


def test_make_credential_event_serializa_campos_sin_mutar():
    fields = [
        CredentialField("username", "alice", "user", 0.99),
        CredentialField("password", "SuperSecret123", "password", 1.0),
    ]
    event = make_credential_event(
        source_ip="192.168.1.23",
        destination_ip="192.168.1.7",
        host="lab.local",
        method="POST",
        path="/login",
        fields=fields,
        synthetic=True,
    )

    assert event["type"] == "credential"
    assert event["synthetic"] is True
    assert event["fields"][0] == {
        "name": "username",
        "value": "alice",
        "category": "user",
        "confidence": 0.99,
    }
    assert fields[0].value == "alice"


def test_make_dns_event_y_stats_event_son_json_serializables():
    dns = make_dns_event("192.168.1.23", "8.8.8.8", "example.com", "A")
    stats = make_stats_event(10, 2, 1, 3, 2.5, 1, 0)

    assert dns["query"] == "example.com"
    assert dns["encrypted"] is False
    assert stats["dnsQueries"] == 3
    json.dumps([dns, stats])


def test_make_hello_event_valida_modo():
    hello = make_hello_event("lab-1", "Wi-Fi", "demo", ["http", "dns"])
    assert hello["mode"] == "demo"
    assert hello["synthetic"] is True

    with pytest.raises(ValueError):
        make_hello_event("lab-1", "Wi-Fi", "offensive", [])


def test_make_error_event():
    event = make_error_event("capture_error", "Npcap no está disponible")
    assert event["type"] == "error"
    assert event["code"] == "capture_error"
