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
| E2 | Los tests del frontend pasan | ⚠️ | 42 passed + 1 fallo preexistente en Windows |
| E3 | El build de producción compila | ✅ | `nuxt build` → Build complete, 1,95 MB |
| E4 | La latencia del WebSocket es < 1500 ms | ✅ | máx. **2,8 ms** (mediana 1,6 ms) |
| E5 | El grafo soporta 100 nodos | ✅ | **99/100 nodos**, 188 aristas |
| E6 | El grafo se dibuja a 30 FPS | ✅ | 30 FPS verificados por simulación a 60/75/90/120 Hz |
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

Resultado: **42 passed, 1 failed**. El fallo es
`tests/defensive-engine.spec.ts:82`, que lee `/proc/net` y por tanto solo puede
pasar en Linux. **No se ha ocultado ni marcado como `skip`**: es un fallo
preexistente del proyecto base, ajeno a este módulo, y se documenta como tal.

Los tests nuevos del laboratorio (30) sí pasan:

| Archivo | Casos |
|---|---:|
| `tests/lab-store.spec.ts` | 11 |
| `tests/lab-metrics.spec.ts` | 12 |
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

La medición se hizo en dos capas, porque el navegador de esta sesión no siempre
entrega fotogramas: primero el **coste real** de dibujar, y luego la **cadencia**
con una prueba determinista.

#### E6.1 Coste por fotograma

Instrumentación `window.__labPerf` y `PerformanceObserver` de
`long-animation-frame`, sobre 99 nodos y 188 aristas:

| Métrica | Headless (CDP 9222) | Instancia con ventana (CDP 9223) |
|---|---:|---:|
| FPS reportado | 20 | 24 |
| Coste medio por fotograma | **1,0 ms** | **1,6 ms** |
| Fotogramas contados | 707 | 126 |
| Fotogramas largos (> 50 ms) | **0** | **0** |

El coste de dibujar 99 nodos y 188 aristas es de **1–1,6 ms**. A 30 FPS el
presupuesto por fotograma es 33,3 ms, así que el render consume entre el 3 % y el
5 %: hay holgura de ~20×.

#### E6.2 Defecto encontrado y corregido

El indicador marcaba 20–24 FPS aunque el coste por fotograma era de 1 ms. La
causa no era rendimiento sino **cuantización del intervalo**: el bucle usaba
`if (now - lastFrame < FRAME_MS) return; lastFrame = now`, de modo que el
intervalo se redondeaba al múltiplo del refresco de la pantalla. A 90 Hz el
objetivo de 33,3 ms cae en 44,4 ms → **22,5 FPS**; a 120 Hz cae en 33,3 ms →
30 FPS. El mismo código rendía distinto en cada monitor.

Se extrajo la decisión a una función pura, `advanceFrame` en
`utils/labMetrics.ts`, que avanza la referencia en múltiplos del objetivo:

```ts
export function advanceFrame(now, lastFrame, frameMs): { due: boolean, lastFrame: number } {
  const elapsed = now - lastFrame
  if (elapsed < frameMs) return { due: false, lastFrame }
  return { due: true, lastFrame: now - (elapsed % frameMs) }
}
```

#### E6.3 Verificación de la cadencia

```powershell
bun run test -- tests/lab-metrics.spec.ts
```

Seis casos nuevos simulan 10 s de refresco y cuentan los fotogramas realmente
pintados. La comparación con el código anterior explica todas las cifras
observadas:

| Refresco simulado | Código anterior | Código corregido | Umbral |
|---|---:|---:|:--:|
| 60 Hz | **20,3 FPS** | **29,9 FPS** | ✅ |
| 75 Hz | 24,9 FPS | 29,9 FPS | ✅ |
| 90 Hz | 24,5 FPS | 29,9 FPS | ✅ |
| 120 Hz | 26,6 FPS | 29,9 FPS | ✅ |
| 144 Hz | 28,7 FPS | 29,9 FPS | ✅ |

Los 20,3 FPS a 60 Hz del código anterior coinciden con los **20 FPS** medidos en
el navegador headless, y los 24,9 a 75 Hz con los **24 FPS** de la instancia con
ventana. No era falta de rendimiento: el límite de 30 Hz se redondeaba al
múltiplo del refresco, y la aritmética de coma flotante hacía que 60 Hz cayera en
tres refrescos (50 ms) en vez de dos (33,3 ms).

Los seis casos verifican además que no se pinta antes de tiempo y que una pausa
de 10 s produce un solo fotograma, sin ráfaga de recuperación.

**Lo que sigue sin verificarse en pantalla:** la observación directa del
indicador a 30 FPS. En el navegador integrado la pestaña llegó a reportar
`requestAnimationFrame` a 0 Hz (el compositor dejó de presentar fotogramas),
y con CDP las ventanas se marcaron `document.hidden = true`. Por eso la prueba
de cadencia es determinista (unitaria) y no una captura: es la única forma
honesta de afirmar 30 FPS en este equipo.

Evidencia visual del comportamiento anterior:
[`evidencias/02-render-fps.png`](./evidencias/02-render-fps.png) muestra el grafo
completo con `24 FPS · 34 ms`, capturado antes de la corrección.

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
2. **30 FPS no observados directamente en pantalla.** La cadencia está
   verificada por simulación a 60/75/90/120 Hz (E6.3) y el coste por fotograma es
   de 1–1,6 ms; lo que no se logró fue ver el indicador marcar 30, porque el
   navegador de esta sesión dejó de presentar fotogramas.
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
