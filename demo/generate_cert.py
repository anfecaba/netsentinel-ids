"""Genera un certificado autofirmado para el servidor HTTPS de laboratorio.

Crea `certs/lab.key` y `certs/lab.crt` con SAN para `127.0.0.1` y `localhost`.
El navegador mostrará una advertencia de certificado no confiable: es
esperado. Se acepta solo en el equipo de laboratorio.

Uso:
    python generate_cert.py
    python generate_cert.py --days 30 --force
"""

from __future__ import annotations

import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

CERT_DIR = Path(__file__).resolve().parent / "certs"
KEY_PATH = CERT_DIR / "lab.key"
CERT_PATH = CERT_DIR / "lab.crt"


def generate(days: int = 30, force: bool = False) -> tuple[Path, Path]:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise SystemExit(
            "Falta el paquete 'cryptography'. Instálalo con:\n"
            "  cd capture && uv sync --extra demo\n"
            "o\n"
            "  python -m pip install cryptography"
        ) from error

    if CERT_PATH.exists() and KEY_PATH.exists() and not force:
        return KEY_PATH, CERT_PATH

    CERT_DIR.mkdir(parents=True, exist_ok=True)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CO"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NetSentinel Lab"),
            x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
        ]
    )

    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    KEY_PATH.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_PATH.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return KEY_PATH, CERT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Certificado autofirmado para la demo HTTPS")
    parser.add_argument("--days", type=int, default=30, help="Validez en días")
    parser.add_argument("--force", action="store_true", help="Regenerar aunque exista")
    args = parser.parse_args()

    key_path, cert_path = generate(args.days, args.force)
    print(f"[demo] clave:        {key_path}")
    print(f"[demo] certificado:  {cert_path}")
    print("[demo] Autofirmado: el navegador avisará de certificado no confiable (esperado).")
    print("[demo] No se suben a git: demo/certs/ está ignorado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
