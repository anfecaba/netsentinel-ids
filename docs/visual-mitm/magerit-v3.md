# Análisis de riesgos con MAGERIT v3 — Laboratorio Visual MITM

> **Naturaleza del documento.** Adaptación académica de MAGERIT v3 al alcance
> concreto de NetSentinel IDS y su módulo de laboratorio. No es una auditoría
> oficial ni sustituye a la herramienta MAGERIT del PAe. La escala de valoración
> es propia (1–5) y se explica para que cualquiera pueda recalcularla.
>
> Fuente metodológica: PAe, *MAGERIT v3 — Metodología de Análisis y Gestión de
> Riesgos de los Sistemas de Información*
> (<https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html>,
> consultado el 2026-10-31).

## 1. Qué aporta MAGERIT al proyecto

MAGERIT propone un proceso iterativo: identificar los activos y sus
dependencias, valorarlos según las dimensiones de seguridad, identificar las
amenazas y vulnerabilidades que los acechan, estimar el impacto, calcular el
riesgo y seleccionar salvaguardas. El resultado se documenta y se revisa
periódicamente.

Aplicado a un laboratorio de captura pasiva, el valor está en separar dos cosas
que suelen confundirse:

1. **El riesgo del sistema que se audita** (una red que usa HTTP en claro).
2. **El riesgo que introduce la propia herramienta de auditoría** (un sniffer
   que podría ver tráfico ajeno, un dashboard que podría exponer credenciales).

Este documento cubre el segundo caso, que es el que compete al proyecto, y usa
el primero como escenario observado.

## 2. Dimensiones de valoración

MAGERIT valora cada activo en varias dimensiones. Para este alcance se usan
cinco, con la escala cualitativa de la tabla.

| Nivel | Valor | Descripción operativa |
|---|---|---|
| Insignificante | 1 | La pérdida no afecta a nadie fuera del aula |
| Menor | 2 | Molestia recuperable sin coste apreciable |
| Medio | 3 | Afecta a la privacidad o a la demo, recuperable con esfuerzo |
| Alto | 4 | Expone credenciales reales o inutiliza el laboratorio |
| Crítico | 5 | Consecuencia legal o académica grave, difícil de revertir |

| Dimensión | Pregunta que responde |
|---|---|
| Disponibilidad (D) | ¿Qué pasa si el servicio no está? |
| Integridad (I) | ¿Qué pasa si los datos se alteran? |
| Confidencialidad (C) | ¿Qué pasa si alguien más los ve? |
| Autenticidad (A) | ¿Podemos probar quién originó el dato? |
| Trazabilidad (T) | ¿Podemos reconstruir qué ocurrió y cuándo? |

## 3. Inventario de activos

| Código | Activo | Tipo | Descripción | D | I | C | A | T |
|---|---|---|---|---|:-:|:-:|:-:|:-:|:-:|
| `INFO-CRED` | Credenciales observadas | Dato | Usuario y contraseña capturados en el POST de laboratorio | 2 | 5 | 5 | 4 | 3 |
| `INFO-TRAF` | Metadatos de tráfico | Dato | IPs, puertos, DNS, tamaños y horas | 2 | 4 | 4 | 3 | 4 |
| `INFO-AUT` | Autorización escrita | Dato legal | Permiso del responsable de la red | 3 | 5 | 3 | 5 | 5 |
| `SW-CAP` | Motor de captura (`capture/`) | Software | Scapy + ensamblador HTTP + extracción | 4 | 4 | 3 | 4 | 4 |
| `SW-DASH` | Dashboard (`/laboratorio`) | Software | Nuxt + Pinia + Canvas + d3-force | 4 | 3 | 3 | 3 | 3 |
| `COM-WS` | Canal WebSocket | Comunicación | `ws://127.0.0.1:8765` con eventos JSON | 4 | 4 | 4 | 4 | 4 |
| `HW-HOST` | Equipo de captura | Hardware | Portátil del laboratorio con Npcap/libpcap | 3 | 3 | 4 | 3 | 2 |
| `NET-LAB` | Red de laboratorio | Red | Switch, AP propio o loopback | 4 | 3 | 4 | 3 | 2 |
| `SVC-DNS` | Resolución DNS | Servicio externo | Resolver usado por el cliente observado | 3 | 3 | 4 | 3 | 3 |
| `LEG-DOC` | Informe y evidencias | Documento | Entregable académico con capturas | 3 | 4 | 3 | 4 | 5 |

**Valor acumulado** (máximo de las dimensiones, criterio conservador):

| Activo | Valor | Justificación breve |
|---|---:|---|
| `INFO-CRED` | 5 | Una contraseña real expuesta es irreversible |
| `INFO-AUT` | 5 | Sin autorización, la actividad es delictiva |
| `INFO-TRAF` | 4 | Revela hábitos y topología |
| `COM-WS` | 4 | Transporta credenciales en memoria |
| `SW-CAP` | 4 | Si falla, no hay evidencia que entregar |
| `SW-DASH` | 4 | Es la interfaz evaluada por el docente |
| `NET-LAB` | 4 | Compartida con otros servicios del aula |
| `HW-HOST` | 4 | Contiene el resto de activos |
| `SVC-DNS` | 4 | Fuera del control del proyecto |
| `LEG-DOC` | 5 | Es el producto evaluable |

## 4. Dependencias

```
LEG-DOC  →  SW-DASH  →  COM-WS  →  SW-CAP  →  NET-LAB  →  HW-HOST
                 ↓                       ↓
             INFO-TRAF              INFO-CRED
                 ↓                       ↓
             SVC-DNS                INFO-AUT  (habilita legalmente todo lo anterior)
```

Lectura: si `INFO-AUT` falta, todo el árbol pasa de "auditoría autorizada" a
"interceptación no autorizada". Por eso su valor es 5 en autenticidad y
trazabilidad, no por su contenido.

## 5. Amenazas y vulnerabilidades

Familias según MAGERIT: **[N]** naturales, **[I]** industriales o fallos
técnicos, **[E]** errores y omisiones, **[A]** ataques intencionados.

| ID | Familia | Amenaza | Activo afectado | Vulnerabilidad que la habilita |
|---|---|---|---|---|
| T-01 | [A] | Interceptación pasiva de tráfico en la red del aula | `INFO-CRED`, `INFO-TRAF` | Segmento compartido sin cifrado ni aislamiento |
| T-02 | [A] | Suplantación ARP para desviar tráfico | `NET-LAB`, `INFO-TRAF` | Ausencia de DAI/ARP inspection en el switch |
| T-03 | [A] | Acceso no autorizado al WebSocket desde la LAN | `COM-WS` | Bind a `0.0.0.0` sin token ni validación de `Origin` |
| T-04 | [A] | Fuga de credenciales por log persistente | `INFO-CRED` | Uso de `--log-raw` o logs de proxy con cuerpo |
| T-05 | [E] | Captura en una red sin autorización | `INFO-AUT` | Operador sin permiso escrito; el guard legal es solo una bandera |
| T-06 | [E] | Confundir simulación con captura real | `LEG-DOC` | No revisar el rótulo `synthetic` ni el modo `hello` |
| T-07 | [I] | Caída de la captura por falta de Npcap/libpcap | `SW-CAP` | Dependencia de driver externo y de permisos de administrador |
| T-08 | [I] | Saturación del navegador por ráfaga de eventos | `SW-DASH` | Ingesta sin límite de cola ni poda de estructuras |
| T-09 | [I] | Red conmutada/WPA2 impide ver tráfico de terceros | `NET-LAB` | Promiscuidad inútil sin puerto espejo o AP propio |
| T-10 | [N] | Corte de energía durante la demo | `HW-HOST`, `SW-DASH` | Sin SAI ni guion alternativo |
| T-11 | [A] | Alteración de la evidencia entregada | `LEG-DOC` | Capturas sin metadatos ni comandos reproducibles |

## 6. Estimación del riesgo inherente

**Modelo:** `riesgo = valor del activo (1–5) × probabilidad (1–5)`, sobre 25.
Clasificación: **Bajo** 1–4 · **Medio** 5–9 · **Alto** 10–16 · **Crítico** 17–25.

Probabilidad: 1 remota, 2 improbable, 3 posible, 4 probable, 5 casi segura
en el contexto del aula.

| ID | Activo | Valor | Prob. | Riesgo | Nivel |
|---|---|:-:|:-:|:-:|---|
| T-01 | `INFO-CRED` | 5 | 4 | 20 | **Crítico** |
| T-02 | `NET-LAB` | 4 | 2 | 8 | Medio |
| T-03 | `COM-WS` | 4 | 3 | 12 | Alto |
| T-04 | `INFO-CRED` | 5 | 3 | 15 | Alto |
| T-05 | `INFO-AUT` | 5 | 2 | 10 | Alto |
| T-06 | `LEG-DOC` | 5 | 3 | 15 | Alto |
| T-07 | `SW-CAP` | 4 | 4 | 16 | Alto |
| T-08 | `SW-DASH` | 4 | 4 | 16 | Alto |
| T-09 | `NET-LAB` | 4 | 5 | 20 | **Crítico** |
| T-10 | `HW-HOST` | 4 | 2 | 8 | Medio |
| T-11 | `LEG-DOC` | 5 | 2 | 10 | Alto |

Los dos riesgos críticos tienen tratamiento distinto:

- **T-01** se reduce con salvaguardas técnicas (TLS, HSTS, DoT) y de alcance
  (solo tráfico propio).
- **T-09** no se resuelve con software: se resuelve cambiando el escenario
  (loopback, contenedor o AP de laboratorio). El proyecto lo declara como
  **limitación**, no como algo que la herramienta pueda sortear.

## 7. Salvaguardas y riesgo residual

| Salvaguarda | Amenazas | Implementación en el proyecto | Riesgo residual |
|---|---|---|:-:|
| Captura pasiva sin inyección | T-02 | `CaptureEngine` solo lee; no hay ARP spoofing ni envío de paquetes | T-02 → 3 |
| Guard de autorización | T-05, T-01 | `--i-have-authorization` obligatorio; sin él, salida con código 2 | T-05 → 4 |
| Bind local por defecto | T-03 | `127.0.0.1:8765`; fuera de loopback exige `--token` y valida `Origin` | T-03 → 4 |
| Redacción de logs y sin persistencia | T-04 | `_redact()` sustituye valores por `[REDACTADO]`; `--log-raw` es opt-in; el dashboard guarda en memoria Pinia | T-04 → 5 |
| Rótulo de simulación | T-06 | `synthetic: true` en todos los eventos de `--demo`; badge **SIMULACIÓN** | T-06 → 5 |
| Ingesta por lotes y poda | T-08 | Lote de 100 ms, tope de 600 pendientes, 500 flujos / 100 nodos / 200 DNS | T-08 → 8 |
| Mensajes de error explícitos | T-07 | `RuntimeError` con instrucciones de Npcap/libpcap; nunca falla en silencio | T-07 → 12 |
| Guion con comandos y capturas | T-11 | `docs/visual-mitm/demo-http-vs-https.md` + `evidencias.md` | T-11 → 5 |
| TLS 1.2+ y HSTS en el sistema auditado | T-01 | Recomendación, no implementación del proyecto | T-01 → 12 |
| DoH/DoT en el cliente auditado | T-01 | Recomendación | T-01 → 12 |
| DAI / ARP inspection | T-02 | Recomendación para el switch del aula | T-02 → 2 |
| 802.1X y segmentación | T-01, T-09 | Recomendación de red | T-09 → 16 |
| SAI o batería | T-10 | Recomendación de infraestructura | T-10 → 4 |

### Riesgo residual agregado

| Nivel | Inherente | Residual | Comentario |
|---|---:|---:|---|
| Crítico | 2 | 0 | Ambos críticos bajan a Alto o Medio |
| Alto | 7 | 3 | Persisten T-07, T-09 y T-01 en su parte de red |
| Medio | 2 | 4 | T-04, T-06, T-08 y T-11 se quedan en Medio |
| Bajo | 0 | 4 | T-02, T-03, T-05 y T-10 |

**Lo que no se puede reducir desde el código:** el riesgo de observar una red
compartida sin cifrado (T-01) y el de que la red conmutada oculte el tráfico
(T-09). Ambas son propiedades del entorno, y por eso el informe final las
presenta como límites del experimento.

## 8. Ejemplo de cálculo reproducible

Para `INFO-CRED` frente a T-01:

```
valor(INFO-CRED)   = 5  (confidencialidad Crítica: una contraseña real no se "desexpone")
probabilidad(T-01) = 4  (en un aula con HTTP y Wi-Fi compartido, es probable)
riesgo inherente   = 5 × 4 = 20  → Crítico

tras TLS 1.3 + HSTS en el sistema auditado:
probabilidad(T-01) = 2  (solo metadatos; el cuerpo ya no es legible)
riesgo residual    = 5 × 2 = 10  → Alto (sigue siendo alto por el valor del activo)
```

El ejemplo muestra la propiedad incómoda del modelo: **una salvaguarda técnica
no convierte un activo crítico en riesgo bajo**; solo reduce la probabilidad.
La decisión de aceptar el riesgo residual es del responsable del sistema, no de
la herramienta.

## 9. Revisión

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-31 | Versión inicial alineada con el módulo `laboratorio` |

Próxima revisión sugerida: al cerrar el semestre, o antes si cambia el
escenario de red del aula.
