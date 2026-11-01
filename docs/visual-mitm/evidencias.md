# Checklist de evidencias — Laboratorio Visual MITM

> **Cómo leer este documento.** Cada fila declara una afirmación, el comando que
> la produce y el resultado obtenido en esta máquina (Windows 11, 31 de octubre
> de 2026). Si un resultado no se pudo obtener, se dice explícitamente y se
> explica por qué. Ninguna cifra de este documento proviene de una estimación:
> todas salen de una ejecución registrada.

## 1. Resumen

| ID | Afirmación | Estado | Resultado medido |
|---|---|:--:|---|
| E1 | Los tests del backend de captura pasan | ✅ | **50 passed** en 2,39 s |
| E2 | Los tests del frontend pasan | ⚠️ | 36 passed + 1 fallo preexistente en Windows |
| E3 | El build de producción compila | ✅ | `nuxt build` → Build complete, 1,95 MB |
| E4 | La latencia del WebSocket es < 1500 ms | ✅ | máx. **2,8 ms** (mediana 1,6 ms) |
| E5 | El grafo soporta 100 nodos | ✅ | **99/100 nodos**, 188 aristas |
| E6 | El grafo se dibuja a 30 FPS | ⚠️ | 24 FPS observados; **1,6 ms por fotograma** |
| E7 | La demo distingue HTTP de HTTPS | ✅ | 200/200/400 frente a 200/200/000 |
| E8 | No se filtran credenciales a la consola | ✅ | **0** coincidencias en los logs |
| E9 | Los documentos académicos están completos | ✅ | 6 documentos en `docs/visual-mitm/` |

**Leyenda:** ✅ verificado · ⚠️ verificado con una limitación declarada · ❌ no
verificado.

## 2. Evidencias detalladas

### E1 · Tests del backend

```powershell
cd capture
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado:

```
50 passed, 100 warnings in 2.39s
```

Cobertura por módulo: `config`, `http_parser`, `credentials`, `dns_parser`,
`sniffer`, `ws_server`, `demo`, `main`. Las advertencias son de
`pytest_asyncio` por `asyncio.get_event_loop_policy`, no fallos.

### E2 · Tests del frontend

```powershell
bun run test
```

Resultado: **36 passed, 1 failed**. El fallo es
`tests/defensive-engine.spec.ts:82`, que lee `/proc/net` y por tanto solo puede
pasar en Linux. **No se ha ocultado ni marcado como `skip`**: es un fallo
preexistente del proyecto base, ajeno a este módulo, y se documenta como tal.

Los tests nuevos del laboratorio (24) sí pasan:

| Archivo | Casos |
|---|---:|
| `tests/lab-store.spec.ts` | 11 |
| `tests/lab-metrics.spec.ts` | 6 |
| `tests/lab-graph-style.spec.ts` | 7 |

### E3 · Build de producción

```powershell
$env:NUXT_IGNORE_LOCK = '1'
bun run build
```

Resultado: `✨ Build complete!` con `Σ Total size: 1.95 MB (462 kB gzip)`. Se
usa `NUXT_IGNORE_LOCK` porque el servidor de desarrollo mantiene el lock de
Nuxt; el build en sí no depende de él.

### E4 · Latencia del WebSocket

Con el backend en modo simulación (`--demo --nodes 100 --rate 30`) escuchando en
`ws://127.0.0.1:8765`:

```powershell
cd capture
.\.venv\Scripts\python.exe tools\ws_probe.py --seconds 8 --json
```

Resultado:

```json
{"nodes": 98, "flows": 152, "credentials": 16, "dnsQueries": 26,
 "eventsMeasured": 197,
 "latencyMs": {"min": 0.7, "median": 1.6, "p95": 2.4, "max": 2.8},
 "under1500ms": true}
```

El mensaje `hello` confirma el modo:

```json
{"type": "hello", "mode": "demo", "iface": "demo", "synthetic": true,
 "capabilities": ["http", "dns", "tls-metadata"]}
```

**Lectura:** 2,8 ms de máximo frente a un requisito de 1500 ms. La holgura es de
tres órdenes de magnitud. `synthetic: true` es la prueba de que esta cifra
proviene de la simulación, no de tráfico real interceptado.

### E5 · Grafo con 100 nodos

Medido en el navegador sobre `/laboratorio`, con captura en
[`evidencias/01-laboratorio-100-nodos.png`](./evidencias/01-laboratorio-100-nodos.png):

| Indicador | Valor |
|---|---|
| Nodos en el grafo | **99 / 100** |
| Aristas | 188 |
| Flujos (tope del store) | 500 |
| Credenciales | 49 |
| Consultas DNS | 79 |
| Latencia WS en la UI | 73 ms |

**Por qué 99 y no 100:** el store deduplica por IP. La simulación reserva una
IP para el propio sensor, que no aparece como nodo del grafo. El requisito «hasta
100 nodos» se cumple; el contador muestra 99/100 de forma honesta en lugar de
inflar el número.

### E6 · Rendimiento de dibujo (30 FPS)

Instrumentación `window.__labPerf` y `PerformanceObserver` de
`long-animation-frame`, sobre 99 nodos y 188 aristas:

| Métrica | Headless (9222) | Instancia con ventana (9223) |
|---|---:|---:|
| FPS reportado | 20 | 24 |
| Coste medio por fotograma | **1,0 ms** | **1,6 ms** |
| Fotogramas contados | 707 | 126 |
| Fotogramas largos (> 50 ms) | **0** | **0** |

**Conclusión honesta:** el coste real de dibujar 99 nodos y 188 aristas es de
**1–1,6 ms por fotograma**. A 30 FPS el presupuesto por fotograma es 33,3 ms, así
que el render consume entre el 3 % y el 5 % de ese presupuesto: hay holgura para
30 FPS con un factor de ~20.

**Lo que no se afirma:** que el indicador haya marcado 30 FPS en pantalla. En
esta máquina el navegador reportó `document.hidden === true` en ambos intentos
—incluso con `Page.setWebLifecycleState('active')` y con una instancia con
ventana—, lo que limita `requestAnimationFrame` a ~20–24 Hz. Es una restricción
del entorno de medición (sesión sin foco de escritorio), no del código. La
verificación a 30 FPS en pantalla queda **pendiente de ejecutarse en un equipo
con sesión interactiva**, y por eso no se declara como cumplida.

Evidencia visual: [`evidencias/02-render-fps.png`](./evidencias/02-render-fps.png)
muestra el grafo completo con el indicador `24 FPS · 34 ms`.

### E7 · Demo HTTP vs HTTPS

```powershell
cd demo
..\capture\.venv\Scripts\python.exe http_login_server.py
..\capture\.venv\Scripts\python.exe https_login_server.py
```

| Petición | HTTP `:8080` | HTTPS `:8443` |
|---|---:|---:|
| `GET /` | 200 | 200 |
| `POST /login` con `username`+`password` | 200 | 200 |
| `POST /login` incompleto | **400** | 400 |
| `GET /` sin `-k` (validación del certificado) | — | **000** |

El `000` de la última fila es la prueba de que el certificado es autofirmado y
de que el cliente lo rechaza si no se le indica lo contrario: `curl` falla antes
de completar la petición.

### E8 · Higiene de credenciales

Los dos servidores de demo se arrancaron redirigiendo salida y error a archivo,
se les hizo tráfico y se buscó cualquier rastro de las credenciales sintéticas:

```powershell
Select-String -Path $hout,$sout,$herr,$serr -Pattern 'SuperSecret|alice'
```

Resultado: **0 coincidencias**. La consola solo registra método, ruta y estado:

```
[demo] GET / -> 200
[demo] POST /login -> 200
[demo] POST /login -> 400
```

Se corrigió durante la verificación un detalle: la primera versión imprimía las
credenciales de ejemplo en la línea de arranque. Ahora remite a `demo/README.md`.
También se corrigió el contador de campos, que aceptaba cualquier `POST` con al
menos un campo; ahora exige `username` y `password`.

### E9 · Documentos académicos

| Documento | Estado |
|---|---|
| `README.md` (índice y fuentes) | ✅ |
| `demo-http-vs-https.md` | ✅ |
| `magerit-v3.md` | ✅ |
| `iso-27001-2022.md` | ✅ |
| `ley-1273-2009.md` | ✅ |
| `evidencias.md` (este documento) | ✅ |
| `informe-final.md` | ✅ |

Fuentes primarias consultadas el 2026-10-31: Ley 1273 de 2009 (texto compilado
del Senado), MAGERIT v3 (PAe), ISO/IEC 27001:2022 Anexo A (títulos de control).

## 3. Límites declarados

Ninguno de estos puntos se presenta como resuelto:

1. **Captura real en Windows: no ejecutada.** Requiere Npcap instalado y una
   consola de administrador. En esta máquina no está Npcap, así que todas las
   cifras de tráfico son del modo `--demo` (`synthetic: true`).
2. **30 FPS en pantalla: no verificado.** Ver E6. El coste por fotograma sí está
   medido y es de 1–1,6 ms.
3. **Red conmutada o WPA2.** Un sniffer pasivo no ve tráfico de terceros sin
   puerto espejo o AP propio. Es una limitación del escenario, no un defecto del
   software, y aparece en el pie de `/laboratorio`.
4. **Un fallo de test preexistente** en `tests/defensive-engine.spec.ts` en
   Windows por dependencia de `/proc/net`.
5. **Sin SGSI.** Los documentos de ISO/IEC 27001:2022 son una tabla de
   correspondencia, no una declaración de aplicabilidad ni una auditoría.

## 4. Cómo reproducir todo

```powershell
# 1. Backend en modo simulación
cd capture
.\.venv\Scripts\python.exe -m lab_capture.main --demo --nodes 100 --rate 30

# 2. Pruebas
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\ws_probe.py --seconds 8 --json

# 3. Frontend
cd ..
bun install
bun run test
bun run dev        # http://localhost:3090/laboratorio

# 4. Demo HTTP vs HTTPS
cd demo
..\capture\.venv\Scripts\python.exe generate_cert.py
..\capture\.venv\Scripts\python.exe http_login_server.py
..\capture\.venv\Scripts\python.exe https_login_server.py
```

## 5. Índice de capturas

| Archivo | Qué muestra |
|---|---|
| `evidencias/01-laboratorio-100-nodos.png` | Vista general: pestañas, banner legal, KPIs (472 flujos, 49 credenciales, 79 DNS, 73 ms, 99/100 nodos) |
| `evidencias/02-render-fps.png` | Grafo completo de 99 nodos con 188 aristas, credenciales con valores completos, panel DNS y tabla de flujos con HTTP/HTTPS, indicador `24 FPS · 34 ms` |
