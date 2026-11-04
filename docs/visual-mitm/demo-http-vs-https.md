# Guion de la demo — HTTP vs HTTPS con captura pasiva

| Campo | Valor |
|---|---|
| Objetivo | Demostrar, con evidencia visual, que HTTP expone credenciales y HTTPS no |
| Duración estimada | 25–35 minutos (incluye preparación y capturas) |
| Requisitos | Proyecto NetSentinel IDS en la rama `dev`, `uv`, navegador, Npcap (Windows) o libpcap (Linux) |

> **Antes de empezar.** La captura real exige `--i-have-authorization` y una red
> propia o autorizada por escrito. Usa solo las credenciales sintéticas
> `alice` / `SuperSecret123`. Lee `ley-1273-2009.md` si tienes cualquier duda sobre
> el alcance.

Los resultados de cada paso se anotan en [`evidencias.md`](evidencias.md). Este
guion describe **qué debería ocurrir**; no contiene mediciones inventadas. Todo lo
que no se haya ejecutado aparece allí como `PENDIENTE`.

---

## 0. Preparación del entorno

### 0.1 Comprobar puertos y dependencias

```powershell
# Windows — PowerShell
Get-NetTCPConnection -LocalPort 3090,8080,8443,8765 -State Listen -ErrorAction SilentlyContinue
```

```bash
# Linux / macOS
ss -ltnp 'sport = :3090 or sport = :8080 or sport = :8443 or sport = :8765'
```

Sin salida = puertos libres. Si algo está ocupado, ciérralo antes de continuar.

```powershell
# Windows
bun install
..\capture\.venv\Scripts\python.exe demo\generate_cert.py
```

```bash
# Linux / macOS
bun install
./capture/.venv/bin/python demo/generate_cert.py
```

> Alternativa sin depender del venv del proyecto:
> `uv run --no-project --with cryptography python demo/generate_cert.py`
> (descarga `cryptography` en un entorno efímero la primera vez).

El certificado debe existir en `demo/certs/lab.crt` y `demo/certs/lab.key`. Si ya
existía, añade `--force` (con el servidor HTTPS detenido).

### 0.2 Levantar la interfaz

```powershell
# Terminal A — Windows
bun run dev
```

```bash
# Terminal A — Linux / macOS
bun run dev
```

Abre <http://localhost:3090/laboratorio>. La pestaña debe cargar el banner legal,
los KPI en cero y el estado vacío con los comandos sugeridos.

### 0.3 Levantar los servidores de demo

```powershell
# Terminal B — Windows (HTTP)
cd demo
..\capture\.venv\Scripts\python.exe http_login_server.py

# Terminal C — Windows (HTTPS)
cd demo
..\capture\.venv\Scripts\python.exe https_login_server.py
```

```bash
# Terminal B y C — Linux / macOS
cd demo
../capture/.venv/bin/python http_login_server.py
../capture/.venv/bin/python https_login_server.py
```

Comprobación rápida (debe imprimir `200` dos veces):

```powershell
curl.exe -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8080/login -d "username=alice&password=SuperSecret123"
curl.exe -k -s -o NUL -w "%{http_code}" -X POST https://127.0.0.1:8443/login -d "username=alice&password=SuperSecret123"
```

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://127.0.0.1:8080/login -d "username=alice&password=SuperSecret123"
curl -k -s -o /dev/null -w "%{http_code}" -X POST https://127.0.0.1:8443/login -d "username=alice&password=SuperSecret123"
```

> Este paso verifica los **servidores**, no la captura. Ejecutado el 2026-10-31:
> `200`/`200` con credenciales válidas, `400` con el formulario incompleto y
> `000` en HTTPS sin `-k` (el certificado autofirmado se rechaza). Resultados en
> [`evidencias.md`](evidencias.md), sección E7.

---

## Paso A — Validar la UI con tráfico sintético (`--demo`)

**Propósito:** comprobar que el grafo, los KPI y el medidor funcionan **sin tocar
la red**, antes de introducir tráfico real. Así se separa un fallo de interfaz de
un fallo de captura.

```powershell
# Terminal D — Windows
cd capture
uv run python -m lab_capture.main --demo --nodes 100 --rate 30
```

```bash
# Terminal D — Linux / macOS
cd capture
uv run python -m lab_capture.main --demo --nodes 100 --rate 30
```

Qué debe ocurrir:

1. El proceso abre el WebSocket en `127.0.0.1:8765` e imprime el modo `demo`.
2. En `/laboratorio`, el indicador de conexión pasa a *conectado*.
3. Aparece la etiqueta **SIMULACIÓN** (eventos con `synthetic: true`).
4. El grafo se llena hasta 100 nodos (IPs `10.10.0.x`).
5. El KPI de FPS se estabiliza y el de latencia muestra un valor bajo.
6. Cada cierto número de eventos aparece una credencial sintética
   `alice` / `SuperSecret123`.

Criterio de aceptación (ver `docs/superpowers/specs/2026-10-29-visual-mitm-lab-design.md` §9):

- FPS ≥ 30 con 100 nodos.
- Latencia < 1.5 s.

**Anota los valores reales** en `evidencias.md`. Si no alcanzan el umbral, no los
"redondees": registra el valor y explica la causa.

Detén el proceso con `Ctrl+C` antes de pasar a la captura real.

---

## Paso B — Iniciar la captura real (`--i-have-authorization`)

**Propósito:** capturar tráfico propio del equipo, de forma pasiva.

### B.1 Windows (Npcap + administrador)

1. Instala **Npcap** (modo compatible con WinPcap si otra herramienta lo requiere).
2. Abre **PowerShell como administrador**.
3. Lista interfaces y localiza la de tu conexión (Ethernet/Wi-Fi) o el adaptador
   de loopback si Npcap lo expone:

```powershell
cd capture
uv run python -m lab_capture.main --list-ifaces
```

4. Arranca la captura con el nombre exacto de la interfaz:

```powershell
uv run python -m lab_capture.main --iface "<NOMBRE_DE_LA_INTERFAZ>" --i-have-authorization
```

### B.2 Linux

```bash
cd capture
uv run python -m lab_capture.main --list-ifaces
sudo uv run python -m lab_capture.main --iface lo --i-have-authorization
```

`lo` captura el tráfico de loopback, que es exactamente donde viven los servidores
de demo (8080/8443). Si vas a capturar una interfaz física, sustitúyela por
`wlo1`, `eth0`, etc.

### B.3 Qué verificar

- El proceso imprime que la captura está activa y que el WebSocket escucha.
- En `/laboratorio`, `SYNTHETIC` desaparece y la conexión queda en *conectado*.
- **No** debe aparecer tráfico ajeno: si ves IPs que no son de tu equipo ni del
  loopback, detén la captura y revisa el alcance.

> **Nota Windows:** Npcap puede no capturar loopback según la instalación. Si
> `lo`/`Loopback` no entrega paquetes, haz la demo entre dos máquinas de una LAN de
> laboratorio (o equipo + VM) y anótalo en `evidencias.md`. No simules el
> resultado.

---

## Paso C — Demostración por HTTP

1. Abre <http://127.0.0.1:8080/> en el navegador.
2. Verifica el badge **HTTP · contenido en texto plano**.
3. Escribe usuario `alice` y contraseña `SuperSecret123`.
4. Pulsa **Enviar credenciales de prueba**.

Resultado esperado:

| Observación | Dónde se ve |
|---|---|
| Respuesta `200` con "Credenciales recibidas" | Navegador |
| Evento `credential` con `POST /login` | Panel de credenciales del laboratorio |
| Campos `username=alice` y `password=SuperSecret123` en claro | Misma tarjeta |
| Arista y nodo marcados en rojo (pulso temporal) | Grafo |
| Flujo HTTP con `encrypted: false` | Tabla de flujos |
| Consola del servidor: `POST /login -> 200`, sin valores | Terminal B |

**No debe aparecer** ninguna fila de credencial en la consola del servidor: la
captura ocurre en la red, no en el servidor.

---

## Paso D — Demostración por HTTPS

1. Abre <https://127.0.0.1:8443/>.
2. Acepta la advertencia del certificado autofirmado (*Avanzado* → *Continuar*).
3. Comprueba el badge **HTTPS · contenido cifrado con TLS**.
4. Envía las **mismas** credenciales `alice` / `SuperSecret123`.

Resultado esperado:

| Observación | Dónde se ve |
|---|---|
| Evento `flow` con `encrypted: true` y nota de metadatos TLS | Tabla de flujos |
| **Ningún** evento `credential` nuevo | Panel de credenciales |
| Sin nodo rojo nuevo por ese flujo | Grafo |
| Consola del servidor: `POST /login -> 200 (TLSv1.3)` | Terminal C |

Si aparece una credencial en este paso, la prueba **falla**: revisa que estés en
el puerto 8443 con `https://` y que no haya un proxy que termine TLS.

Qué **sí** se observa en HTTPS (y conviene mencionar en el informe): IP de origen
y destino, puertos, nombre del servidor en el saludo TLS (SNI), tamaños y tiempos.
Eso permite inferir a qué servicio se conecta alguien aunque no se lea el
contenido: es el riesgo residual de la sección 5 de `magerit-v3.md`.

---

## Paso E — Medir latencia y FPS

### E.1 Latencia

- La UI calcula `latencyMs = ahora − capturedAt` y lo muestra en los KPI.
- Observa al menos **30 eventos** seguidos y anota el máximo, no solo el mejor.
- Umbral de aceptación: **< 1.5 s**.
- Si capturas entre dos máquinas, el reloj puede desfasarse: mide en el mismo
  equipo o sincroniza con NTP y dilo en el informe.

### E.2 FPS con 100 nodos

- Ejecuta `--demo --nodes 100 --rate 30` (Paso A) y deja correr **60 segundos**.
- El medidor de la UI muestra los FPS efectivos del grafo.
- Umbral de aceptación: **≥ 30 FPS**.

### E.3 Cómo registrar la medición

| Métrica | Valor observado (2026-10-31) | Umbral | ¿Cumple? | Método |
|---|---|---|---|---|
| FPS con 100 nodos | **29,9 FPS** medidos en pantalla (120 Hz) y en simulación de 60 a 144 Hz · 1,0 ms por fotograma | ≥ 30 | ✅ | Indicador de la UI + `window.__labPerf` + `tests/lab-metrics.spec.ts` |
| Latencia máxima | **2,8 ms** (mediana 1,6) | < 1.5 s | ✅ | `ws_probe.py`, 197 eventos |
| Nodos dibujados | **99 / 100** | 100 | ✅ | Contador del grafo |

El indicador de la UI marcaba 20–24 FPS porque el límite de 30 Hz se cuantizaba
al refresco de la pantalla (el código anterior daba 20,3 FPS a 60 Hz). Se
corrigió con `advanceFrame`: tras el cambio se midieron **29,9 FPS en pantalla**
(180 fotogramas en 6,02 s a 120 Hz) y 29,9 FPS en simulación a 60, 75, 90, 120 y
144 Hz. Detalle en [`evidencias.md`](evidencias.md), sección E6.

No copies valores de ejemplo: si vuelves a medir, sustituye estos números por los
tuyos y deja `PENDIENTE` lo que no hayas ejecutado.

---

## Paso F — Capturar evidencias

Nombra las capturas con un patrón estable y guárdalas fuera de `demo/certs/`:

```
docs/visual-mitm/evidencias/
  01-laboratorio-100-nodos.png    ✅ ya generada
  02-render-fps.png               ✅ ya generada
  03-http-credencial-detectada.png
  04-https-solo-metadatos.png
  05-consola-servidor-redactada.png
```

Las dos primeras existen y están referenciadas en
[`evidencias.md`](evidencias.md). El resto corresponde al bloque de captura real
(con Npcap/administrador), todavía no ejecutado.

Checklist de cada captura:

- [ ] Se ve la URL o el panel que identifica el paso.
- [ ] Se ve la fecha/hora del sistema (barra de tareas o reloj de la UI).
- [ ] No hay credenciales reales ni datos de terceros.
- [ ] El valor de FPS y latencia es legible (no recortado).
- [ ] El archivo está en PNG, sin compresión con pérdida.

Recomendaciones:

- Captura la **ventana completa**, no solo el fragmento, para que se entienda el
  contexto.
- Si publicas el informe, verifica que ninguna captura incluya rutas con tu nombre
  de usuario de Windows.
- Calcula el hash de cada archivo si necesitas trazabilidad:

```powershell
Get-FileHash docs/visual-mitm/evidencias/*.png -Algorithm SHA256 | Format-Table
```

```bash
sha256sum docs/visual-mitm/evidencias/*.png
```

---

## Resumen de resultados esperados

| Paso | Entrada | Resultado esperado | Evidencia |
|---|---|---|---|
| A | `--demo --nodes 100 --rate 30` | 100 nodos, ≥ 30 FPS, latencia < 1.5 s, etiqueta SIMULACIÓN | Captura 01–02 |
| B | `--i-have-authorization --iface …` | Captura activa, conexión establecida | Registro en consola |
| C | `POST` HTTP con `alice` | Credencial visible + nodo rojo | Capturas 03–04 |
| D | `POST` HTTPS con `alice` | Solo flujo cifrado, sin credencial | Capturas 05–06 |
| E | Observación de KPI | Valores anotados con método | Tabla de métricas |
| F | Capturas + hashes | Checklist completo | `evidencias.md` |

---

## Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| La pestaña queda en *desconectado* | El proceso de captura no arrancó o el puerto 8765 está ocupado | Revisa la Terminal D; `Get-NetTCPConnection -LocalPort 8765` |
| `--i-have-authorization` no está: el proceso sale con código 2 | Gate legal | Añade el flag solo si tienes autorización |
| No se captura nada en Windows | Falta Npcap o la shell no es de administrador | Reinstala Npcap, abre PowerShell como administrador |
| No se captura en loopback | Limitación de Npcap | Usa la interfaz LAN con equipo + VM y documéntalo |
| Aparece credencial en HTTPS | Proxy que termina TLS o puerto equivocado | Comprueba la URL y desactiva proxies |
| El navegador no carga HTTPS | Certificado no generado o servidor caído | Ejecuta `generate_cert.py`, revisa la Terminal C |
| FPS por debajo de 30 | Pestaña en segundo plano, equipo limitado | Mantén la pestaña visible; mide de nuevo y anota el valor real |

---

## Cierre

1. `Ctrl+C` en las terminales B, C y D.
2. Verifica que no queden puertos escuchando (comando del paso 0.1).
3. Borra las capturas que no vayas a usar y cualquier log temporal.
4. Completa [`evidencias.md`](evidencias.md) y continúa con
   [`informe-final.md`](informe-final.md).
