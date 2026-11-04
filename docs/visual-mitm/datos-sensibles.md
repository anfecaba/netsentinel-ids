# Qué datos sensibles maneja el proyecto y qué se construyó

Resumen de una página para quien revise el repositorio sin contexto previo.
No sustituye al [`informe-final.md`](./informe-final.md): lo resume.

---

## 1. Qué es sensible aquí

El proyecto captura tráfico HTTP y DNS. Eso significa que **puede ver
credenciales en texto plano**. Es el hallazgo pedagógico, y también su único
riesgo real.

| Dato sensible | Dónde vive | Se guarda en disco | Cómo se protege |
|---|---|---|---|
| **Credenciales capturadas** (usuario, contraseña, cookies, `Authorization: Basic`) | Memoria del navegador (store de Pinia) y del proceso Python | **No** | El frontend no usa `localStorage`, `sessionStorage` ni cookies; al cerrar la pestaña desaparecen. El evento existe solo en RAM. |
| **Valores sintéticos de la demo** (`alice` / `SuperSecret123`) | `demo/`, `docs/`, `capture/tests/`, `capture/lab_capture/demo.py` | Sí, en el repo | Son inventados y están declarados como tales. No pertenecen a ninguna persona. |
| **Logs de captura** | `capture/logs/` (ignorado por git) | Solo si se pasa `--log` | El log escribe `[REDACTADO]` en cada campo. Para volcar credenciales en claro hay que pedir `--log-raw` explícitamente, y el programa imprime una advertencia. |
| **Clave privada del certificado TLS** de la demo | `demo/certs/lab.key` | Sí, en el equipo | `demo/certs/` está en `.gitignore`. Se regenera con `demo/generate_cert.py`; nunca se sube. |
| **Token del WebSocket** (solo al exponer el backend en LAN) | Argumento `--token` en memoria | No | Obligatorio si `--host` no es localhost, más validación del encabezado `Origin`. |
| **Capturas de tráfico** (`.pcap`, `.pcapng`) | Donde el usuario las guarde | Solo si se generan aparte | `*.pcap` y `*.pcapng` están ignorados. El programa no escribe capturas por sí mismo. |
| **Capturas de pantalla del repo** | `docs/visual-mitm/evidencias/` | Sí, en el repo | Muestran únicamente credenciales sintéticas (`alice`), tráfico de loopback y datos del propio laboratorio. |
| **Variables de entorno / secretos de despliegue** | — | **No existen** | `.env` y `.env.*` ignorados; el proyecto no necesita ninguna clave para funcionar. |

**Lo que no hay en el repositorio:** credenciales reales, datos personales de
terceros, claves privadas, tokens de API, capturas de tráfico ni `.env`.

**Riesgo residual honesto:** las capturas de pantalla sí muestran la contraseña
sintética en claro. Es deliberado —el objetivo es que se vea—, pero significa
que esas imágenes no deben reutilizarse en un entorno con datos reales.

---

## 2. Qué se construyó

Partiendo de un IDS defensivo que leía `/proc/net/*`, se añadió un segundo
módulo que demuestra, con tráfico real o simulado, por qué TLS importa.

| Pieza | Qué hace | Dónde |
|---|---|---|
| **Backend de captura** (Python + Scapy) | Lee la NIC en modo promiscuo, reconstruye HTTP, extrae credenciales, parsea DNS y publica JSON por WebSocket | `capture/lab_capture/` |
| **Servidor WebSocket** | Bind `127.0.0.1:8765`, token y `Origin` al exponerse en LAN | `capture/lab_capture/ws_server.py` |
| **CLI con control legal** | Sin `--i-have-authorization` imprime el aviso y sale con código 2 | `capture/lab_capture/main.py` |
| **Generador sintético** | 100 nodos a 30 eventos/s para medir sin tocar la red; todo marcado `synthetic: true` | `capture/lab_capture/demo.py` |
| **Página `/laboratorio`** | Grafo d3-force en Canvas, KPIs, credenciales, DNS y tabla de flujos | `pages/laboratorio.vue` + `components/lab/` |
| **Corrección de rendimiento** | El límite de 30 FPS se cuantizaba al refresco de pantalla (20,3 FPS a 60 Hz); se corrigió con `advanceFrame` | `utils/labMetrics.ts` |
| **Demo HTTP vs HTTPS** | Dos servidores locales que muestran el mismo login en claro y cifrado | `demo/` |
| **Entregables académicos** | MAGERIT v3, ISO/IEC 27001:2022, Ley 1273 de 2009, checklist de evidencias e informe | `docs/visual-mitm/` |

**Verificado, no estimado:** 50 tests de backend y 42 de frontend en verde
(más un fallo preexistente en Windows por `/proc/net`), build de producción
correcto, 2,8 ms de latencia máxima por WebSocket, 99/100 nodos y 29,9 FPS
medidos en pantalla a 120 Hz.

**No verificado:** la captura real en Windows. No hay Npcap instalado en el
equipo donde se desarrolló, así que todas las cifras de tráfico son del modo
`--demo`. El código de captura está probado con paquetes construidos en memoria,
pero nunca ha leído una interfaz física en esta máquina. Está declarado así en
`evidencias.md` e `informe-final.md`.

---

## 3. Si vas a ejecutarlo

```powershell
# Sin tocar la red
cd capture
uv run python -m lab_capture.main --demo --nodes 100 --rate 30

# Captura real: solo en red propia y con autorización escrita
uv run python -m lab_capture.main --iface "Wi-Fi" --i-have-authorization
```

En Windows la captura real exige Npcap y PowerShell como administrador. En
Linux, `libpcap-dev` y `sudo`. Sin `--i-have-authorization` el programa se
detiene: no hay forma de saltarse ese control desde la interfaz.
