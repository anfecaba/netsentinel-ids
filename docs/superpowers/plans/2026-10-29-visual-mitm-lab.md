# Visual MITM Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrar en NetSentinel una pestaña de laboratorio que capture tráfico HTTP/DNS con Scapy, extraiga credenciales en texto plano y las visualice en un grafo Canvas a 30 FPS y latencia menor a 1.5 s.

**Architecture:** Un proceso Python independiente (`capture/`) escucha con Scapy, parsea HTTP/DNS y publica eventos JSON por WebSocket. La SPA Nuxt se conecta directamente a `ws://127.0.0.1:8765`, valida con Zod, actualiza Pinia y dibuja con `d3-force` + Canvas. La pestaña Defensa existente no se modifica funcionalmente.

**Tech Stack:** Python 3.8+, Scapy 2.5, websockets 12, pytest; Nuxt 3.13, Pinia, Zod, d3-force, Canvas, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-29-visual-mitm-lab-design.md`

## Global Constraints

- Captura **solo pasiva**: prohibido ARP spoofing, SSL stripping, inyección o ruptura de TLS.
- La captura real exige `--i-have-authorization`; sin el flag, el proceso termina con código 2 y muestra el aviso legal.
- Sin persistencia de credenciales por defecto. `--log` redacta valores; `--log-raw` es explícito.
- WebSocket en `127.0.0.1:8765` por defecto; para LAN exige `--token` y valida `Origin`.
- Credenciales de demo sintéticas: `alice` / `SuperSecret123`. Nunca credenciales reales.
- La pestaña Defensa debe seguir compilando y funcionando.
- Todos los eventos llevan `type`, `capturedAt` ISO 8601 UTC y `synthetic`.
- El límite del grafo es 100 nodos; los flujos se agregan por par origen-destino-protocolo.
- El render del grafo se capped a 30 FPS; el medidor se muestra en la UI.

## Review Focus

- Peticiones HTTP fragmentadas, con `Content-Length` incorrecto o sin body: no deben bloquear el sniffer ni inventar credenciales.
- Formularios con nombres en español, JSON anidado, arrays o `Authorization: Basic`: deben detectarse con confianza y sin falsos positivos evidentes.
- WebSocket caído, cliente lento o mensaje inválido: la UI debe reconectar, descartar el evento y seguir viva.
- Ráfagas de 100+ nodos y muchos eventos: el grafo debe mantener 30 FPS, limitar memoria y no congelar la pestaña.
- Windows sin Npcap o sin permisos: debe fallar con un mensaje accionable, no con un traceback ni con datos simulados presentados como reales.

---

### Task 0: Preparar rama y línea base

**Files:**
- Modify: ninguno
- Test: comandos de verificación

**Interfaces:**
- Consumes: repo actual en `main`
- Produces: rama `dev` local actualizada, dependencias instaladas

- [ ] **Step 1: Cambiar a la rama de desarrollo**

```bash
git fetch origin
git checkout -b dev origin/dev
git status --short
```

Expected: rama `dev`, árbol limpio.

- [ ] **Step 2: Instalar dependencias actuales**

```bash
bun install
bun run test
bun run build
```

Expected: `bun run test` con 4/5 en Windows (el caso `/proc` falla por entorno); build completo. Registrar la línea base en el commit.

- [ ] **Step 3: Crear estructura de docs y commit inicial**

```bash
mkdir -p capture/lab_capture capture/tests demo docs/visual-mitm
```

```bash
git add docs/superpowers
git commit -m "docs(lab): agrega diseño y plan del Visual MITM"
```

---

### Task 1: Contrato de eventos y modelo de grafo

**Files:**
- Create: `types/lab.ts`
- Create: `utils/labGraphModel.ts`
- Create: `tests/lab-events.spec.ts`
- Create: `tests/lab-graph-model.spec.ts`
- Create: `capture/lab_capture/__init__.py`
- Create: `capture/lab_capture/models.py`
- Create: `capture/tests/test_models.py`
- Create: `capture/pyproject.toml`

**Interfaces:**
- Produces:
  - `LabEventSchema` (Zod discriminated union) y tipos `LabEvent`, `LabFlow`, `LabCredential`, `LabDns`, `LabStats`, `LabHello`, `LabError`
  - `buildLabGraph(flows: LabFlow[], credentials: LabCredential[], maxNodes?: number): LabGraph`
  - Python `make_flow_event(...) -> dict`, `make_credential_event(...) -> dict`, `make_dns_event(...) -> dict`, `make_stats_event(...) -> dict`, `make_hello_event(...) -> dict`

- [ ] **Step 1: Escribir el test de esquemas Zod**

```ts
// tests/lab-events.spec.ts
import { describe, it, expect } from 'vitest'
import { LabEventSchema } from '../types/lab'

describe('LabEventSchema', () => {
  it('acepta un evento credential válido y rechaza uno sin campos', () => {
    const valid = LabEventSchema.safeParse({
      type: 'credential',
      id: 'cred-1',
      capturedAt: new Date().toISOString(),
      sourceIp: '192.168.1.23',
      destinationIp: '192.168.1.7',
      host: 'lab.local',
      method: 'POST',
      path: '/login',
      fields: [{ name: 'password', value: 'x', category: 'password', confidence: 0.99 }],
      synthetic: false
    })
    expect(valid.success).toBe(true)
    expect(LabEventSchema.safeParse({ type: 'credential', id: 'x' }).success).toBe(false)
  })
})
```

- [ ] **Step 2: Ejecutar el test y verlo fallar**

Run: `bun run test tests/lab-events.spec.ts`
Expected: FAIL porque `types/lab.ts` no existe.

- [ ] **Step 3: Implementar `types/lab.ts`**

Define los esquemas con `z.discriminatedUnion('type', [...])`, tipos inferidos y `LabGraphNode`, `LabGraphEdge`, `LabGraph`. Todos los eventos incluyen `capturedAt` ISO y `synthetic` boolean. `fields` exige `name`, `value`, `category` (`user|password|email|token|other`) y `confidence` entre 0 y 1.

- [ ] **Step 4: Escribir el test del modelo de grafo**

```ts
// tests/lab-graph-model.spec.ts
import { describe, it, expect } from 'vitest'
import { buildLabGraph } from '../utils/labGraphModel'
import type { LabFlow, LabCredential } from '../types/lab'

function flow(i: number): LabFlow {
  return {
    type: 'flow', id: `f-${i}`, capturedAt: new Date().toISOString(),
    sourceIp: `10.0.0.${i % 120}`, sourcePort: 5000 + i,
    destinationIp: `10.0.1.${i % 120}`, destinationPort: 80,
    protocol: 'HTTP', encrypted: false, bytes: 100,
    riskLevel: 'danger', synthetic: false
  }
}

describe('buildLabGraph', () => {
  it('limita a 100 nodos y marca la arista con credencial', () => {
    const flows = Array.from({ length: 120 }, (_, i) => flow(i))
    const credential: LabCredential = {
      type: 'credential', id: 'c-1', capturedAt: new Date().toISOString(),
      sourceIp: '10.0.0.1', destinationIp: '10.0.1.1', host: 'lab.local',
      method: 'POST', path: '/login',
      fields: [{ name: 'password', value: 'x', category: 'password', confidence: 0.99 }],
      synthetic: false
    }
    const graph = buildLabGraph(flows, [credential], 100)
    expect(graph.nodes.length).toBeLessThanOrEqual(100)
    expect(graph.edges.some((e) => e.hasCredential)).toBe(true)
  })
})
```

- [ ] **Step 5: Ejecutar el test y verlo fallar**

Run: `bun run test tests/lab-graph-model.spec.ts`
Expected: FAIL porque `utils/labGraphModel.ts` no existe.

- [ ] **Step 6: Implementar `utils/labGraphModel.ts`**

```ts
export function buildLabGraph(
  flows: LabFlow[],
  credentials: LabCredential[],
  maxNodes = 100
): LabGraph
```

Agrupa nodos por IP, aristas por `${sourceIp}->${destinationIp}:${protocol}`, acumula `count`/`bytes`, conserva `lastSeen` máximo y marca `hasCredential` si alguna credencial usa esa arista. Ordena por `lastSeen` descendente y recorta a `maxNodes`. Nunca muta las entradas.

- [ ] **Step 7: Implementar el contrato Python y sus tests**

`capture/lab_capture/models.py` define dataclasses `CredentialField`, `HttpRequest`, `DnsQuery` y funciones `make_*_event(...)` que devuelven dicts camelCase. `capture/tests/test_models.py` verifica claves exactas (`capturedAt`, `sourceIp`, `synthetic`) y que `make_credential_event` no muta los campos.

Run: `cd capture && uv sync && uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add types/lab.ts utils/labGraphModel.ts tests/lab-events.spec.ts tests/lab-graph-model.spec.ts capture/
git commit -m "feat(lab): define contrato de eventos y modelo de grafo"
```

---

### Task 2: Parser HTTP y ensamblador TCP

**Files:**
- Create: `capture/lab_capture/http_parser.py`
- Create: `capture/tests/test_http_parser.py`

**Interfaces:**
- Produces:
  - `parse_http_request(raw: bytes) -> HttpRequest | None`
  - `HttpRequestAssembler.feed(source_ip: str, source_port: int, destination_ip: str, destination_port: int, seq: int, payload: bytes, timestamp: datetime) -> list[HttpRequest]`
  - `HttpRequestAssembler.reset(key: tuple[str, int, str, int]) -> None`

- [ ] **Step 1: Escribir tests de parseo**

Casos:
1. `GET /index.html HTTP/1.1\r\nHost: lab.local\r\n\r\n` → `method=GET`, `path=/index.html`, `host=lab.local`, body vacío.
2. `POST /login HTTP/1.1\r\nHost: lab.local\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 27\r\n\r\nusername=alice&password=123` → body completo.
3. Un request sin `\r\n\r\n` → `None`.
4. `Content-Length` mayor que el body recibido → `None` (esperar más).

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `cd capture && uv run pytest tests/test_http_parser.py -v`
Expected: FAIL por import.

- [ ] **Step 3: Implementar `parse_http_request`**

Usa una regex para la línea de request, parsea headers con `email.parser.BytesHeaderParser` o split manual, respeta `Content-Length`, limita el body a 64 KB y decodifica header names a minúsculas. Devuelve `HttpRequest` con `headers` normalizados y `body: bytes`.

- [ ] **Step 4: Escribir test del ensamblador con dos segmentos**

Divide un POST en dos `payload` con `seq` consecutivos; el primer `feed` devuelve `[]`, el segundo devuelve un `HttpRequest`. Un tercer `feed` con payload basura no debe lanzar excepción.

- [ ] **Step 5: Implementar `HttpRequestAssembler`**

Buffer por 4-tupla; ignora duplicados por `seq`; si el buffer supera 64 KB, lo descarta y registra un contador de descartes. Al completar un request, lo elimina y devuelve una lista (soporta pipelining básico).

- [ ] **Step 6: Ejecutar tests y commit**

Run: `cd capture && uv run pytest tests/test_http_parser.py -v`
Expected: PASS.

```bash
git add capture/lab_capture/http_parser.py capture/tests/test_http_parser.py
git commit -m "feat(lab): parsea peticiones HTTP con ensamblado TCP acotado"
```

---

### Task 3: Extractor de credenciales

**Files:**
- Create: `capture/lab_capture/credentials.py`
- Create: `capture/tests/test_credentials.py`

**Interfaces:**
- Produces:
  - `classify_field(name: str) -> str | None`
  - `extract_from_form(body: bytes) -> list[CredentialField]`
  - `extract_from_json(body: bytes) -> list[CredentialField]`
  - `extract_from_headers(headers: dict[str, str]) -> list[CredentialField]`
  - `extract_credentials(request: HttpRequest) -> list[CredentialField]`

- [ ] **Step 1: Escribir tests de clasificación**

Casos:
- `username`, `user`, `usuario`, `login` → `user`
- `password`, `passwd`, `pwd`, `contrasena`, `clave` → `password`
- `email`, `correo`, `mail` → `email`
- `token`, `access_token`, `sessionid`, `jwt`, `api_key` → `token`
- `comments`, `search` → `None`

- [ ] **Step 2: Escribir tests de extracción**

- Form: `username=alice&password=SuperSecret123&email=alice%40lab.local` → 3 campos.
- JSON: `{"user":{"name":"alice"},"auth":{"password":"SuperSecret123"}}` → 2 campos (aplanado).
- Header: `Authorization: Basic YWxpY2U6U3VwZXJTZWNyZXQxMjM=` → campo `authorization` con valor decodificado.
- Cookie: `Cookie: sessionid=abc123; theme=dark` → solo `sessionid`.
- Valores vacíos o de más de 512 caracteres → se omiten.

- [ ] **Step 3: Ejecutar y ver fallar**

Run: `cd capture && uv run pytest tests/test_credentials.py -v`
Expected: FAIL por import.

- [ ] **Step 4: Implementar el extractor**

Normaliza nombres (`lower`, quita `[]`, `_`, `-`), usa `urllib.parse.parse_qsl` para form, `json.loads` + aplanado recursivo (máx. 3 niveles) para JSON, decodifica Basic auth y parsea cookies. Deduplica por `(name, value)`. Confianza: 0.99 coincidencia exacta, 0.85 contención, 0.90 cookies. No registra valores en logs.

- [ ] **Step 5: Ejecutar tests y commit**

Run: `cd capture && uv run pytest tests/test_credentials.py -v`
Expected: PASS.

```bash
git add capture/lab_capture/credentials.py capture/tests/test_credentials.py
git commit -m "feat(lab): extrae credenciales de formularios, JSON y cabeceras"
```

---

### Task 4: Parser DNS

**Files:**
- Create: `capture/lab_capture/dns_parser.py`
- Create: `capture/tests/test_dns_parser.py`

**Interfaces:**
- Produces:
  - `parse_dns_packet(packet: Packet, captured_at: datetime | None = None) -> dict | None`
  - `QTYPE_NAMES: dict[int, str]`

- [ ] **Step 1: Escribir test con un paquete Scapy**

```python
from scapy.all import IP, UDP, DNS, DNSQR
pkt = IP(src="192.168.1.23", dst="8.8.8.8")/UDP(sport=53000, dport=53)/DNS(rd=1, qd=DNSQR(qname="example.com", qtype="A"))
event = parse_dns_packet(pkt)
assert event["type"] == "dns"
assert event["query"] == "example.com"
assert event["qtype"] == "A"
assert event["encrypted"] is False
```

También un paquete de respuesta (`qr=1`) devuelve `None`, y un paquete sin DNS devuelve `None`.

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `cd capture && uv run pytest tests/test_dns_parser.py -v`
Expected: FAIL por import.

- [ ] **Step 3: Implementar `parse_dns_packet`**

Extrae `IP.src`, `IP.dst`, `UDP.sport`, `UDP.dport`, `DNSQR.qname`, `DNSQR.qtype`. Normaliza el nombre sin punto final. Mapea qtype a `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `SOA`, `PTR`, `HTTPS` o `TYPE-<n>`. Devuelve `None` si `DNS.qr == 1`.

- [ ] **Step 4: Ejecutar tests y commit**

Run: `cd capture && uv run pytest tests/test_dns_parser.py -v`
Expected: PASS.

```bash
git add capture/lab_capture/dns_parser.py capture/tests/test_dns_parser.py
git commit -m "feat(lab): parsea consultas DNS sin cifrar"
```

---

### Task 5: Motor de captura Scapy

**Files:**
- Create: `capture/lab_capture/config.py`
- Create: `capture/lab_capture/sniffer.py`
- Create: `capture/tests/test_sniffer.py`

**Interfaces:**
- Produces:
  - `CaptureEngine(iface: str, on_event: Callable[[dict], None], bpf_filter: str = DEFAULT_BPF)`
  - `CaptureEngine.start() -> None` (bloqueante, para hilo)
  - `CaptureEngine.stop() -> None`
  - `CaptureEngine.handle_packet(packet: Packet) -> None`
  - `list_interfaces() -> list[dict]`

- [ ] **Step 1: Escribir tests de `handle_packet` con paquetes sintéticos**

1. Paquete TCP/80 con POST completo → dos eventos: `flow` HTTP y `credential`.
2. Paquete TCP/443 → un evento `flow` con `encrypted=True`, sin `credential`.
3. Paquete UDP/53 con DNS query → eventos `dns` y `flow`.
4. Paquete no IP → no emite nada.
5. Paquete TCP/80 con body incompleto → no emite `credential`.

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `cd capture && uv run pytest tests/test_sniffer.py -v`
Expected: FAIL por import.

- [ ] **Step 3: Implementar `CaptureEngine`**

`handle_packet` usa `IP in packet`; para TCP llama al ensamblador y, por cada request, crea `flow` y, si hay campos, `credential`. Para UDP/53 usa `parse_dns_packet`. Para TCP/443/8443 crea `flow` TLS con `encrypted=True` y `note="Solo metadatos TLS; el payload no se descifra"`. `start()` llama `sniff(iface=..., filter=..., prn=self.handle_packet, store=False, promisc=True)`. `stop()` usa `conf.stop_sniffing()` o un flag.

- [ ] **Step 4: Implementar `list_interfaces`**

Windows: `get_windows_if_list()` con nombre, descripción y MAC. Linux: `get_if_list()`. Devuelve una lista serializable para `--list-ifaces`.

- [ ] **Step 5: Ejecutar tests y commit**

Run: `cd capture && uv run pytest tests/test_sniffer.py -v`
Expected: PASS.

```bash
git add capture/lab_capture/config.py capture/lab_capture/sniffer.py capture/tests/test_sniffer.py
git commit -m "feat(lab): captura pasiva HTTP, DNS y metadatos TLS con Scapy"
```

---

### Task 6: WebSocket, CLI y modo demo

**Files:**
- Create: `capture/lab_capture/ws_server.py`
- Create: `capture/lab_capture/demo.py`
- Create: `capture/lab_capture/main.py`
- Create: `capture/tests/test_demo.py`
- Create: `capture/tests/test_ws_server.py`
- Create: `capture/README.md`

**Interfaces:**
- Produces:
  - `LabHub(host: str, port: int, token: str | None, allowed_origins: list[str])`
  - `LabHub.broadcast(event: dict) -> None`
  - `LabHub.run() -> None` (async)
  - `DemoGenerator(nodes: int, rate: float).events()` (async iterator)
  - CLI `python -m lab_capture.main --demo --nodes 100 --rate 30`

- [ ] **Step 1: Escribir tests del generador demo**

Verifica que `--nodes 5 --rate 10` produce eventos con `synthetic=True`, IDs únicos y al menos un `credential` cada 10 eventos. Verifica que el hello incluye `mode="demo"`.

- [ ] **Step 2: Ejecutar y ver fallar**

Run: `cd capture && uv run pytest tests/test_demo.py -v`
Expected: FAIL por import.

- [ ] **Step 3: Implementar `demo.py`**

Generador asíncrono que alterna `flow` HTTP, `credential` y `dns`; usa IPs `10.10.0.x` y credenciales sintéticas `alice`/`SuperSecret123`; respeta `rate` con `asyncio.sleep(1/rate)`; marca `synthetic=True`.

- [ ] **Step 4: Implementar `ws_server.py`**

`websockets.serve` con handler `(websocket, path)`. Valida `Origin` contra `allowed_origins` y token de query si está configurado. Envía `hello` al conectar. `broadcast` serializa JSON, usa `asyncio.wait_for(ws.send(...), 1.0)` y elimina clientes lentos o cerrados.

- [ ] **Step 5: Implementar `main.py`**

Argparse con `--iface`, `--host` (default `127.0.0.1`), `--port` (default `8765`), `--token`, `--demo`, `--nodes`, `--rate`, `--list-ifaces`, `--i-have-authorization`, `--log`, `--log-raw`, `--filter`. Flujo:
1. Si `--list-ifaces`, imprime y sale.
2. Si no `--demo` y no `--i-have-authorization`, imprime aviso legal y sale con 2.
3. Inicia hub WS.
4. Si `--demo`, consume `DemoGenerator`; si no, inicia `CaptureEngine` en un hilo y puentea eventos con `loop.call_soon_threadsafe`.
5. Ctrl+C detiene captura y cierra clientes.

- [ ] **Step 6: Escribir test de integración WS**

Levanta `LabHub` en puerto efímero, conecta `websockets.connect`, espera `hello`, envía un `flow` con `broadcast` y verifica que llega. Prueba token inválido → cierre 1008.

Run: `cd capture && uv run pytest tests/test_ws_server.py -v`
Expected: PASS.

- [ ] **Step 7: Documentar instalación y uso**

`capture/README.md` con Windows (Npcap, admin), Linux (libpcap, root), `uv sync`, `--list-ifaces`, `--demo`, `--i-have-authorization`, límites de red y aviso legal.

- [ ] **Step 8: Commit**

```bash
git add capture/
git commit -m "feat(lab): servidor WebSocket, CLI y modo demo sintético"
```

---

### Task 7: Store, socket y métricas del frontend

**Files:**
- Create: `stores/lab.store.ts`
- Create: `composables/useLabSocket.ts`
- Create: `utils/labMetrics.ts`
- Create: `tests/lab-store.spec.ts`
- Create: `tests/lab-metrics.spec.ts`

**Interfaces:**
- Produces:
  - `useLabStore()` con `connection`, `serverInfo`, `flowsById`, `credentials`, `dnsQueries`, `stats`, `lastError`, `isPaused`, `selectedNodeId`, `graph`, `latencyMs`, `ingest(event)`, `clear()`, `setFps(n)`, `selectNode(ip)`
  - `useLabSocket(options?: { url?: string })` con `connect()`, `disconnect()`, `status`
  - `calculateLatencyMs(capturedAt: string, now = Date.now()): number`
  - `class FpsMeter { tick(now): void; get fps(): number }`

- [ ] **Step 1: Escribir tests del store**

- `ingest` de un `flow` lo agrega a `flowsById` y actualiza `graph`.
- `ingest` del mismo `flow.id` no duplica.
- `ingest` de 600 flujos conserva como máximo 500.
- `ingest` de `credential` lo agrega y marca la arista.
- `clear()` vacía flujos, credenciales, DNS y selección.
- `latencyMs` se calcula con `capturedAt`.

Run: `bun run test tests/lab-store.spec.ts`
Expected: FAIL por import.

- [ ] **Step 2: Implementar `stores/lab.store.ts`**

Usa `defineStore('lab', () => {...})`. Diccionarios normalizados por id, arreglos acotados (`flows` 500, `credentials` 100, `dns` 200), `graph` computed con `buildLabGraph`. No persiste nada. `ingest` ignora eventos inválidos (el socket ya validó) y respeta `isPaused` para flujos/DNS, pero **siempre** ingresa credenciales (una credencial no se debe perder por pausa).

- [ ] **Step 3: Implementar `useLabSocket.ts`**

Usa `useRuntimeConfig().public.labWsUrl` o `options.url`. Crea `WebSocket`, valida cada mensaje con `LabEventSchema`, llama `store.ingest`. Reconexión exponencial 500 ms → 10 s. `onUnmounted(disconnect)`. Estado `idle|connecting|open|closed|error`. No reintenta si el usuario llamó `disconnect()`.

- [ ] **Step 4: Implementar `utils/labMetrics.ts` y tests**

`calculateLatencyMs` devuelve `Math.max(0, now - Date.parse(capturedAt))`; si la fecha es inválida, `-1`. `FpsMeter` cuenta frames en una ventana móvil de 1 s. Tests con timestamps fijos.

- [ ] **Step 5: Ejecutar tests y commit**

Run: `bun run test tests/lab-store.spec.ts tests/lab-metrics.spec.ts`
Expected: PASS.

```bash
git add stores/lab.store.ts composables/useLabSocket.ts utils/labMetrics.ts tests/lab-store.spec.ts tests/lab-metrics.spec.ts
git commit -m "feat(lab): store, cliente WebSocket y métricas de latencia/FPS"
```

---

### Task 8: Grafo Canvas con d3-force

**Files:**
- Modify: `package.json` (agregar `d3-force`, `@types/d3-force`)
- Create: `utils/labGraphStyle.ts`
- Create: `components/lab/LabGraphCanvas.vue`
- Create: `tests/lab-graph-style.spec.ts`

**Interfaces:**
- Produces:
  - `LabGraphCanvas` props `{ graph: LabGraph; selectedNodeId?: string | null }`, emits `{ selectNode: [ip: string]; fps: [fps: number] }`
  - `colorForRole(role: LabGraphNode['role']): string`, `radiusForDegree(degree: number): number`

- [ ] **Step 1: Instalar dependencias**

```bash
bun add d3-force
bun add -d @types/d3-force
```

- [ ] **Step 2: Escribir tests de estilo**

`colorForRole('local')` devuelve el token esmeralda; `radiusForDegree(0)` ≥ 6; `radiusForDegree(50)` ≤ 22; `colorForRole` de un rol desconocido devuelve el gris.

Run: `bun run test tests/lab-graph-style.spec.ts`
Expected: FAIL por import.

- [ ] **Step 3: Implementar `labGraphStyle.ts` y `LabGraphCanvas.vue`**

Canvas con `devicePixelRatio`, `ResizeObserver`, `forceSimulation` con `forceLink`, `forceManyBody`, `forceCenter`, `forceCollide`. Preserva posiciones por `id` al actualizar. Renderiza aristas con alpha y nodos con color/radio; pulso rojo si `hasCredential` y `Date.now() - lastCredentialAt < 10_000`. Etiquetas solo para nodos con `degree >= 3` o seleccionados. `requestAnimationFrame` con acumulador para tick/render a 30 Hz; pausa si `document.hidden`. Emite `fps` cada segundo con `FpsMeter`.

- [ ] **Step 4: Verificar build y rendimiento sintético**

Run: `bun run build`
Expected: build completo.

Run: `cd capture && uv run python -m lab_capture.main --demo --nodes 100 --rate 30`
Expected: servidor WS en 8765. Abrir `/laboratorio`; el grafo muestra 100 nodos y FPS ≥ 30. Anotar el resultado en `docs/visual-mitm/evidencias.md`.

- [ ] **Step 5: Commit**

```bash
git add package.json bun.lock utils/labGraphStyle.ts components/lab/LabGraphCanvas.vue tests/lab-graph-style.spec.ts
git commit -m "feat(lab): grafo Canvas con d3-force, 100 nodos y 30 FPS"
```

---

### Task 9: Pestaña Laboratorio y navegación

**Files:**
- Create: `components/lab/LabWarningBanner.vue`
- Create: `components/lab/LabKpiRow.vue`
- Create: `components/lab/LabCredentialFeed.vue`
- Create: `components/lab/LabDnsFeed.vue`
- Create: `components/lab/LabFlowTable.vue`
- Create: `components/lab/LabEmptyState.vue`
- Create: `pages/laboratorio.vue`
- Modify: `layouts/default.vue`
- Create: `error.vue`

**Interfaces:**
- Consumes: `useLabStore`, `useLabSocket`, `LabGraphCanvas`
- Produces: ruta `/laboratorio`, navegación Defensa/Laboratorio, estados de conexión y vacío

- [ ] **Step 1: Implementar los componentes de presentación**

`LabWarningBanner`: aviso legal fijo con enlace a `docs/visual-mitm/ley-1273-2009.md`. `LabKpiRow`: flujos, credenciales, DNS, latencia, FPS, clientes. `LabCredentialFeed`: tabla con host, método, ruta, hora y campos; valores completos en monoespaciado; botón **Limpiar**; borde rojo y pulso. `LabDnsFeed`: consultas. `LabFlowTable`: flujos recientes con badge de protocolo y candado. `LabEmptyState`: comandos para `--demo` y `--i-have-authorization`.

- [ ] **Step 2: Implementar `pages/laboratorio.vue`**

`onMounted(connect)`, `onUnmounted(disconnect)`. Si `connection === 'error'`, muestra reintento. Si no hay flujos ni credenciales, muestra `LabEmptyState`. Layout responsive: banner, KPIs, grafo (2/3) + credenciales (1/3), DNS + flujos.

- [ ] **Step 3: Modificar `layouts/default.vue`**

Añade `NuxtLink` a `/` y `/laboratorio` con estado activo. En `/`, conserva el badge de postura. En `/laboratorio`, muestra badge de conexión lab y **SOLO LABORATORIO**. El subtítulo cambia por ruta. No rompas el header responsive.

- [ ] **Step 4: Crear `error.vue` global**

Página tematizada con `clearError({ redirect: '/' })`, mensaje y botón de recuperación. No uses la pantalla por defecto de Nuxt.

- [ ] **Step 5: Verificar build y navegación**

Run: `bun run build`
Expected: build completo.

Run: `bun run dev`, abrir `http://localhost:3090/` y `/laboratorio`. Verificar que la pestaña Defensa sigue mostrando KPIs y que Laboratorio muestra el estado vacío sin errores de consola.

- [ ] **Step 6: Commit**

```bash
git add components/lab pages/laboratorio.vue layouts/default.vue error.vue
git commit -m "feat(lab): pestaña Laboratorio, navegación y estados de UI"
```

---

### Task 10: Demo HTTP vs HTTPS y documentos académicos

**Files:**
- Create: `demo/http_login_server.py`
- Create: `demo/https_login_server.py`
- Create: `demo/login.html`
- Create: `demo/generate_cert.py`
- Create: `demo/README.md`
- Create: `docs/visual-mitm/README.md`
- Create: `docs/visual-mitm/magerit-v3.md`
- Create: `docs/visual-mitm/iso-27001-2022.md`
- Create: `docs/visual-mitm/ley-1273-2009.md`
- Create: `docs/visual-mitm/demo-http-vs-https.md`
- Create: `docs/visual-mitm/evidencias.md`
- Create: `docs/visual-mitm/informe-final.md`

**Interfaces:**
- Produces: servidores de laboratorio en `:8080` (HTTP) y `:8443` (HTTPS), documentos citables

- [ ] **Step 1: Investigar y verificar fuentes**

Antes de redactar, verifica con fuentes oficiales:
- Texto y pena del artículo 269C de la Ley 1273 de 2009 (Colombia).
- Estructura de MAGERIT v3 (activos, amenazas, vulnerabilidades, impacto, riesgo, salvaguardas).
- Nombres y números de controles del Anexo A de ISO/IEC 27001:2022 (A.5.15, A.5.17, A.8.5, A.8.12, A.8.15, A.8.16, A.8.20, A.8.21, A.8.24).
Registra las URLs y fechas de consulta en cada documento.

- [ ] **Step 2: Implementar el servidor HTTP de demo**

`http_login_server.py`: `http.server` en `127.0.0.1:8080`, sirve `login.html` y acepta `POST /login` con `username`/`password`; responde 200 con un HTML de “credenciales recibidas” sin registrar el body. No persiste nada.

- [ ] **Step 3: Implementar el servidor HTTPS de demo**

`generate_cert.py` genera `demo/certs/lab.key` y `demo/certs/lab.crt` autofirmados con `cryptography` o `openssl`; `demo/certs/` está en `.gitignore`. `https_login_server.py` envuelve el socket con `ssl.SSLContext` en `127.0.0.1:8443` y sirve el mismo formulario. Documenta la advertencia del navegador.

- [ ] **Step 4: Escribir el guion de demo**

`demo-http-vs-https.md`: pasos exactos para (1) iniciar captura en `--demo` para validar UI, (2) captura real con `--i-have-authorization`, (3) abrir HTTP, enviar `alice`/`SuperSecret123`, ver la credencial y el nodo rojo, (4) abrir HTTPS, enviar las mismas credenciales, verificar que solo aparece metadatos TLS, (5) medir latencia y FPS, (6) capturar evidencias. Incluye comandos de Windows y Linux.

- [ ] **Step 5: Redactar documentos académicos**

- `magerit-v3.md`: inventario de activos (equipos, credenciales, DNS, dashboard, host de captura), matriz amenaza-vulnerabilidad, valoración inherente/residual con escala cualitativa y ejemplo cuantitativo, salvaguardas (TLS 1.3, HSTS, DoH/DoT, DAI, 802.1X, MFA, VPN). Aclara que es una plantilla adaptada, no una auditoría oficial.
- `iso-27001-2022.md`: tabla control → evidencia en NetSentinel → brecha. Enfoca A.8.20, A.8.21, A.8.24, A.8.16, A.8.15, A.8.12, A.5.15, A.5.17, A.8.5.
- `ley-1273-2009.md`: artículo 269C, bien jurídico, pena, diferencia entre captura propia/autorizada y captura de terceros; obligaciones de autorización, minimización y no persistencia; referencia a Ley 1581 de 2012.
- `evidencias.md`: checklist con capturas de 30 FPS, latencia <1.5 s, 100 nodos, credencial HTTP, ausencia de credencial HTTPS, matriz de riesgos.
- `informe-final.md`: estructura del informe extendido (portada, resumen, problema, objetivos, marco legal, metodología MAGERIT, arquitectura, implementación, resultados, análisis de riesgos, conclusiones, recomendaciones, referencias, anexos).

- [ ] **Step 6: Verificar demo HTTP y HTTPS**

Run (terminal 1): `cd demo && uv run python http_login_server.py`
Run (terminal 2): `curl -s -X POST http://127.0.0.1:8080/login -d "username=alice&password=SuperSecret123"` → 200.
Run (terminal 3): `cd demo && uv run python generate_cert.py && uv run python https_login_server.py`
Run: `curl -k -s -X POST https://127.0.0.1:8443/login -d "username=alice&password=SuperSecret123"` → 200.
Expected: ambos responden; ninguno imprime credenciales en consola.

- [ ] **Step 7: Commit**

```bash
git add demo docs/visual-mitm .gitignore
git commit -m "feat(lab): demo HTTP/HTTPS y documentos académicos base"
```

---

### Task 11: QA, evidencias y revisión de seguridad

**Files:**
- Modify: `docs/visual-mitm/evidencias.md`
- Modify: `README.md` (si existe en `dev`)
- Test: comandos completos

**Interfaces:**
- Consumes: todo lo anterior
- Produces: evidencia de aceptación y checklist de seguridad

- [ ] **Step 1: Ejecutar la suite completa**

```bash
bun run test
bun run build
cd capture && uv run pytest -v
```

Expected: Vitest sin fallos nuevos (el caso `/proc` puede fallar solo en Windows; documentarlo), build completo, pytest PASS.

- [ ] **Step 2: Prueba sintética de 100 nodos y 30 FPS**

```bash
cd capture
uv run python -m lab_capture.main --demo --nodes 100 --rate 30
```

Abrir `/laboratorio`, esperar 10 s, capturar pantalla con FPS y latencia. Anotar en `evidencias.md`.

- [ ] **Step 3: Prueba real en loopback o LAN de laboratorio**

En Linux: `sudo uv run python -m lab_capture.main --iface lo --i-have-authorization` (o `wlo1`). En Windows: ejecutar PowerShell como administrador, `uv run python -m lab_capture.main --iface "Loopback" --i-have-authorization`. Abrir el servidor HTTP de demo, enviar credenciales sintéticas y verificar el evento. Si Npcap no captura loopback, usar la interfaz LAN y una VM; documentar el resultado real, no simulado.

- [ ] **Step 4: Prueba HTTPS**

Repetir con el servidor HTTPS. Verificar que **no** aparece una credencial y que solo hay flujos TLS cifrados. Capturar evidencia.

- [ ] **Step 5: Revisión de seguridad**

Checklist:
- `git grep -n "SuperSecret123"` solo en demo/docs/tests, nunca en logs.
- `git status` sin `capture/logs/`, `demo/certs/`, `*.pcap`, `.env`.
- `--i-have-authorization` obligatorio para captura real.
- WS bind localhost por defecto; token/origen si `0.0.0.0`.
- Sin `pickle`, `eval`, `exec` ni deserialización insegura.
- Sin persistencia de credenciales por defecto.
- Banner legal visible en `/laboratorio`.

- [ ] **Step 6: Revisar el diff y commit final**

```bash
git diff dev...HEAD --stat
git status --short
git add -A
git commit -m "test(lab): evidencias de latencia, FPS y demo HTTP vs HTTPS"
```

---

## Self-Review

- **Cobertura del spec:** contrato (§5) → Task 1; parsers (§4) → Tasks 2-4; captura (§4) → Task 5; WS/CLI (§4, §8) → Task 6; store/socket (§7) → Task 7; grafo 30 FPS/100 nodos (§6, §9) → Task 8; UI/pestañas (§7) → Task 9; demo y docs (§10, §14) → Task 10; QA/seguridad (§8, §9, §12) → Task 11.
- **Consistencia de tipos:** `LabFlow`, `LabCredential`, `LabDns`, `LabStats`, `LabHello`, `LabError` se definen en Task 1 y se consumen en Tasks 7-9. `buildLabGraph` se define en Task 1 y se usa en Task 7. `CaptureEngine.handle_packet` se define en Task 5 y se prueba en Task 5. `LabHub.broadcast` se define en Task 6 y se usa en Task 6.
- **Revisión de entradas:** los cinco fallos del `Review Focus` tienen test o verificación explícita en Tasks 2, 3, 6, 8 y 11.
- **Proporción:** el plan describe interfaces y pruebas; los cuerpos de código se dejan al implementador salvo algoritmos que el test no determina.
