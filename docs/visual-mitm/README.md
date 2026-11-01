# Visual MITM — documentación académica

Material de soporte del módulo **Laboratorio** de NetSentinel IDS: captura pasiva
de HTTP y DNS con Scapy, publicada por WebSocket y visualizada en un grafo de
hasta 100 nodos a 30 FPS.

| Documento | Contenido |
|---|---|
| [`demo-http-vs-https.md`](./demo-http-vs-https.md) | Guion reproducible de la comparación HTTP vs HTTPS, con comandos para Windows y Linux |
| [`magerit-v3.md`](./magerit-v3.md) | Análisis de riesgos adaptado a MAGERIT v3: activos, amenazas, valoración y salvaguardas |
| [`iso-27001-2022.md`](./iso-27001-2022.md) | Correspondencia control del Anexo A → evidencia en NetSentinel → brecha |
| [`ley-1273-2009.md`](./ley-1273-2009.md) | Marco penal colombiano, artículo 269C, autorización y minimización |
| [`evidencias.md`](./evidencias.md) | Checklist de evidencias con resultados medidos y límites declarados |
| [`informe-final.md`](./informe-final.md) | Estructura del informe extendido listo para entregar |
| [`evidencias/`](./evidencias/) | Capturas de pantalla referenciadas por el checklist |

## Alcance y honestidad metodológica

- **Captura exclusivamente pasiva.** No hay ARP spoofing, SSL stripping,
  inyección de paquetes ni intento de descifrar TLS. El programa lee lo que la
  interfaz ya recibe.
- **Datos sintéticos por defecto.** El modo `--demo` genera eventos marcados
  `synthetic: true` y la interfaz los rotula como **SIMULACIÓN**.
- **Sin persistencia de credenciales.** Los valores viven en memoria del
  navegador; el log opcional del backend los redacta salvo que se fuerce
  `--log-raw` en un equipo aislado.
- **Los documentos son plantillas adaptadas**, no una auditoría certificada ni
  un dictamen jurídico. MAGERIT v3 e ISO/IEC 27001:2022 se citan como marcos de
  referencia; las valoraciones son del autor del proyecto.

## Cómo reproducir el entorno completo

```powershell
# 1. Backend de captura en modo simulación (no toca la red)
cd capture
uv run python -m lab_capture.main --demo --nodes 100 --rate 30

# 2. Dashboard
cd ..
bun install
bun run dev          # http://localhost:3090/laboratorio

# 3. Servidores de la demo HTTP vs HTTPS
cd demo
..\capture\.venv\Scripts\python.exe http_login_server.py
..\capture\.venv\Scripts\python.exe generate_cert.py
..\capture\.venv\Scripts\python.exe https_login_server.py
```

Para captura real, además: Npcap en Windows (con consola de administrador) o
`libpcap-dev` + `sudo` en Linux, y `--i-have-authorization`.

## Fuentes consultadas

| Fuente | Uso | Consultado |
|---|---|---|
| Ley 1273 de 2009, texto compilado — <http://www.secretariasenado.gov.co/senado/basedoc/ley_1273_2009.html> | Artículos 269A–269J, penas y agravantes | 2026-10-31 |
| MAGERIT v3 — <https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html> | Estructura de la metodología | 2026-10-31 |
| ISO/IEC 27001:2022, Anexo A (93 controles) — <https://www.iso.org/standard/27001> y tabla pública de correspondencia <https://www.isms.online/iso-27001/annex-a-2022/> | Identificadores y títulos de controles | 2026-10-31 |
| OWASP Top 10 — <https://owasp.org/www-project-top-ten/> | Categorías A02 y A07 usadas en el análisis | 2026-10-31 |
