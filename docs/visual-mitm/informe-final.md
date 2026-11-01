# Informe final — Laboratorio Visual MITM con captura pasiva

> **Estado del documento.** Estructura completa y redactada con los resultados
> ya medidos. Los únicos campos vacíos son los de identificación académica, que
> solo tú puedes llenar. Todo lo demás está respaldado por
> [`evidencias.md`](./evidencias.md).

## Portada

| Campo | Valor |
|---|---|
| Título | Laboratorio Visual MITM: captura pasiva de HTTP y DNS con análisis de riesgo y correspondencia normativa |
| Autor | _[tu nombre]_ |
| Programa | Ingeniería de Sistemas — Universidad Cooperativa de Colombia, Villavicencio |
| Curso | _[nombre del curso]_ |
| Docente | _[nombre]_ |
| Fecha | _[fecha de entrega]_ |
| Herramienta | NetSentinel IDS, módulo `laboratorio` |

## 1. Resumen ejecutivo

Se implementó un módulo de laboratorio dentro de NetSentinel IDS que captura
tráfico HTTP y DNS de forma **estrictamente pasiva** con Scapy, lo publica por
WebSocket y lo visualiza en un grafo de fuerza de hasta 100 nodos. El módulo se
acompaña de dos servidores de demostración —uno en HTTP claro y otro en HTTPS con
certificado autofirmado— que sirven el mismo formulario para contrastar qué
observa un sniffer en cada caso.

Resultados medidos: **50 pruebas automatizadas** del backend en verde, latencia
de extremo a extremo de **2,8 ms** en el máximo (requisito: menos de 1500 ms),
grafo estable con **99 de 100 nodos y 188 aristas** y un coste de dibujo de
**1,0–1,6 ms por fotograma**. La demo confirma la diferencia esperada: por HTTP
el formulario es legible, por HTTPS el cuerpo no.

El trabajo se complementa con un análisis MAGERIT v3 (11 amenazas, 2 riesgos
críticos reducidos a 0), una tabla de correspondencia con 9 controles del Anexo A
de ISO/IEC 27001:2022 y el encuadre legal en el artículo 269C de la Ley 1273 de
2009. **No** se realizó ARP spoofing, SSL stripping ni descifrado de TLS.

## 2. Planteamiento del problema

La mayoría de las demostraciones de interceptación en entornos académicos
recurren a técnicas activas: envenenamiento ARP, proxies que degradan TLS o
suplantación de DNS. Son eficaces para la demostración, pero tres problemas:
introducen efectos secundarios en la red, afectan a terceros que no consintieron
y desplazan la discusión técnica hacia la legal. El resultado pedagógico queda
contaminado: el estudiante aprende a "hacer MITM" en lugar de entender **por qué
el texto plano es el problema**.

El problema abordado es entonces: *¿cómo demostrar el riesgo de transmitir
credenciales sin cifrar, con evidencia medible, sin ejecutar ninguna técnica
activa y sin poner en riesgo a terceros?*

## 3. Objetivos

**General.** Implementar un laboratorio de captura pasiva que evidencie la
diferencia entre HTTP y HTTPS, con métricas verificables de latencia y
rendimiento, y enmarcarlo en MAGERIT v3, ISO/IEC 27001:2022 y la Ley 1273 de
2009.

**Específicos.**

1. Capturar y ensamblar tráfico HTTP y DNS con Scapy sin inyectar paquetes.
2. Extraer credenciales transportadas en claro y publicarlas por WebSocket con
   latencia inferior a 1500 ms.
3. Visualizar la topología observada en un grafo de hasta 100 nodos a 30 FPS.
4. Construir una demo reproducible que compare el mismo formulario por HTTP y
   por HTTPS.
5. Documentar el riesgo (MAGERIT), el control (ISO/IEC 27001:2022) y el marco
   legal (Ley 1273 de 2009).

## 4. Marco teórico

| Concepto | Tratamiento en el informe |
|---|---|
| Captura pasiva | La interfaz en modo promiscuo recibe tramas que ya le llegan; no se generan paquetes. Se distingue de la interceptación activa en que no altera el camino del tráfico. |
| MITM | Se explica el modelo clásico y se justifica por qué el laboratorio **no** lo ejecuta: el objetivo es observar, no desviar. |
| TLS | El cifrado protege el cuerpo; los metadatos (IP, puerto, SNI, tamaños, tiempos) siguen visibles. Esa distinción es central en los resultados. |
| DNS | Resolución en claro frente a DoH/DoT; se explica por qué el nombre de dominio revela intención incluso sin ver el contenido. |
| MAGERIT v3 | Metodología de análisis y gestión de riesgos del PAe español: activos, dimensiones, amenazas, salvaguardas, riesgo residual. |
| ISO/IEC 27001:2022 | Sistema de gestión y Anexo A con 93 controles; se usa como catálogo de referencia, no como certificación. |
| Ley 1273 de 2009 | Modifica el Código Penal colombiano y crea el título «De la Protección de la información y de los datos». |

## 5. Metodología

Se trabajó en cinco fases con verificación al cierre de cada una:

1. **Diseño.** Contrato de eventos JSON, arquitectura de tres procesos
   (captura → WebSocket → navegador) y decisiones de seguridad por defecto
   (`127.0.0.1`, guard de autorización, sin persistencia).
2. **Backend.** Módulos independientes con pruebas unitarias por cada parser y
   por el servidor WebSocket.
3. **Frontend.** Store con ingesta por lotes, composable de socket con reconexión
   exponencial y canvas con `d3-force` a 30 Hz.
4. **Demo y documentación.** Servidores HTTP/HTTPS, certificado autofirmado y
   seis documentos académicos.
5. **Verificación.** Pruebas, build, sonda de latencia, medición en navegador y
   revisión de higiene de credenciales.

Herramientas: Python 3.14 con Scapy 2.8 y `websockets` 12; Nuxt 3.13 con Pinia y
`d3-force` 3.0; `uv` y `bun` como gestores de dependencias.

## 6. Desarrollo

### 6.1 Arquitectura

```
[interfaz de red] --(Scapy, solo lectura)--> [CaptureEngine]
                                                   |
                                            eventos JSON
                                                   v
                                        [WebSocket 127.0.0.1:8765]
                                                   |
                                          lote cada 100 ms
                                                   v
                                   [Pinia lab.store] --> [Canvas + d3-force]
```

Tres procesos separados a propósito: si el navegador se satura, la captura no
pierde paquetes; si la captura falla, la UI muestra un error explícito en lugar
de fingir datos.

### 6.2 Contrato de eventos

Cuatro tipos (`hello`, `flow`, `credential`, `dns`) con campos comunes
(`id`, `capturedAt`, `synthetic`) y específicos por tipo. El campo `synthetic`
es el que permite a la interfaz rotular la simulación y al informe distinguir
evidencia real de simulada. El contrato completo está en
`docs/superpowers/specs/2026-10-29-visual-mitm-lab-design.md`.

### 6.3 Decisiones de seguridad

| Decisión | Motivo |
|---|---|
| Bind a `127.0.0.1` por defecto | Evita exponer credenciales a la LAN sin querer |
| `--token` + validación de `Origin` si se expone | Un WebSocket abierto es una fuga esperando ocurrir |
| `--i-have-authorization` obligatorio | Control de proceso; no sustituye autorización legal |
| Redacción de credenciales en log | El log no debe ser un segundo incidente |
| Sin persistencia por defecto | Minimización de datos |
| `--log-raw` explícito y advertido | Solo para equipos aislados |

## 7. Resultados

### 7.1 Pruebas

| Suite | Resultado |
|---|---|
| Backend (`pytest`) | **50 passed** en 2,39 s |
| Frontend (Vitest) | **36 passed**, 1 fallo preexistente en Windows por `/proc/net` |
| Build de producción | `Build complete`, 1,95 MB (462 kB gzip) |

### 7.2 Latencia del canal

| Métrica | Valor | Requisito |
|---|---:|---|
| Mínimo | 0,7 ms | — |
| Mediana | 1,6 ms | — |
| Percentil 95 | 2,4 ms | — |
| **Máximo** | **2,8 ms** | < 1500 ms ✅ |

197 eventos medidos en 8 s con 98 nodos activos.

### 7.3 Grafo

| Métrica | Valor | Requisito |
|---|---:|---|
| Nodos | 99 / 100 | hasta 100 ✅ |
| Aristas | 188 | — |
| Coste por fotograma | 1,0–1,6 ms | 33,3 ms a 30 FPS ✅ |
| Fotogramas largos (> 50 ms) | 0 | 0 ✅ |
| FPS observado en pantalla | 20–24 | 30 ⚠️ |

El límite de FPS observado no proviene del código: el navegador reportó
`document.hidden === true` durante las mediciones, lo que restringe
`requestAnimationFrame`. El coste por fotograma demuestra que el render tiene
holgura de ~20× para 30 FPS.

### 7.4 Demo HTTP vs HTTPS

| Petición | HTTP | HTTPS |
|---|---:|---:|
| `GET /` | 200 | 200 |
| `POST /login` válido | 200 | 200 |
| `POST /login` incompleto | 400 | 400 |
| Sin validar el certificado | — | 000 (rechazado) |

Y el resultado que da sentido a todo: con la captura pasiva activa, el `POST` por
HTTP produce una credencial con **usuario y contraseña completos** en el panel;
el mismo `POST` por HTTPS produce un flujo cifrado **sin credencial**.

### 7.5 Higiene

- 0 apariciones de las credenciales sintéticas en los logs de los servidores.
- Certificados y claves en `demo/certs/`, ignorado por git.
- Sin `.pcap`, sin `capture/logs/` y sin `.env` en el índice.

## 8. Análisis de riesgos (MAGERIT v3)

Resumen; el detalle está en [`magerit-v3.md`](./magerit-v3.md).

| Nivel | Inherente | Residual |
|---|---:|---:|
| Crítico | 2 | **0** |
| Alto | 7 | 3 |
| Medio | 2 | 4 |
| Bajo | 0 | 4 |

Los dos riesgos críticos son la interceptación de credenciales en una red con
texto plano (T-01) y la imposibilidad de ver tráfico en una red conmutada o WPA2
sin puerto espejo (T-09). El primero se reduce con TLS y alcance acotado; el
segundo **no se resuelve con software** y se declara como límite del escenario.

## 9. Correspondencia con ISO/IEC 27001:2022

Resumen; el detalle está en [`iso-27001-2022.md`](./iso-27001-2022.md).

| Control | Título | Madurez |
|---|---|---|
| A.5.15 | Access control | Parcial |
| A.5.17 | Authentication information | Brecha |
| A.8.5 | Secure authentication | Brecha (por diseño) |
| A.8.12 | Data leakage prevention | Parcial |
| A.8.15 | Logging | Parcial |
| A.8.16 | Monitoring activities | Parcial |
| A.8.20 | Networks security | Parcial |
| A.8.21 | Security of network services | Parcial |
| A.8.24 | Use of cryptography | Parcial |

**No se declara conformidad.** No existe SGSI, ni declaración de aplicabilidad
firmada, ni auditoría interna.

## 10. Marco legal

Resumen; el detalle está en [`ley-1273-2009.md`](./ley-1273-2009.md).

El artículo 269C sanciona con prisión de **36 a 72 meses** a quien, sin orden
judicial previa, intercepte datos informáticos en su origen, destino o en el
interior de un sistema. El tipo **no exige ánimo de lucro**. Por eso el proyecto:

1. limita la captura a tráfico propio o a redes con autorización escrita;
2. exige `--i-have-authorization` para captura real;
3. no ejecuta ARP spoofing ni SSL stripping, que agravarían la conducta;
4. usa datos sintéticos en todas las demostraciones.

La autorización del responsable de la red es condición necesaria del ejercicio,
pero **no equivale** a la orden judicial del artículo; el informe lo declara como
zona gris y no como habilitación.

## 11. Limitaciones

1. **Sin captura real en Windows.** No hay Npcap instalado en el equipo de
   trabajo; todas las cifras de tráfico provienen del modo simulación, marcado
   `synthetic: true`.
2. **30 FPS no observados en pantalla.** El coste por fotograma sí está medido
   (1–1,6 ms); la limitación es del entorno de medición.
3. **Red conmutada/WPA2.** Un sniffer pasivo no ve tráfico de terceros sin puerto
   espejo o AP propio.
4. **Un fallo de test preexistente** en Windows por dependencia de `/proc/net`.
5. **Los documentos normativos son adaptaciones académicas**, no auditorías.

## 12. Conclusiones

1. Es posible demostrar el riesgo del texto plano **sin** ejecutar un ataque
   activo: la diferencia entre HTTP y HTTPS se evidencia con dos servidores
   propios en loopback.
2. El coste técnico del enfoque pasivo es bajo: 2,8 ms de latencia máxima y
   1,6 ms por fotograma con 99 nodos, tres órdenes de magnitud por debajo de los
   requisitos de latencia.
3. La parte difícil no es capturar: es **acotar**. El valor del proyecto está en
   los límites explícitos —loopback por defecto, guard legal, redacción de logs,
   sin persistencia— y en declarar lo que no se puede hacer.
4. Los tres marcos se complementan: MAGERIT dice *cuánto duele*, ISO/IEC
   27001:2022 dice *qué control falta* y la Ley 1273 dice *qué riesgo penal
   existe*. Ninguno basta solo.

## 13. Trabajo futuro

| Mejora | Por qué |
|---|---|
| TLS en el WebSocket (`wss://`) con certificado local | Hoy el canal es `ws://` en loopback; fuera de loopback debería cifrarse |
| Captura real con Npcap/libpcap documentada paso a paso | Cierra la limitación 1 |
| Medición de FPS en sesión interactiva | Cierra la limitación 2 |
| Rotación y firma de logs (A.8.15) | Hoy el log es un archivo plano |
| Máscara opcional de credenciales (A.8.11) | Permitiría demos con datos no sintéticos |
| Exportación de evidencia firmada (hash + timestamp) | Refuerza la trazabilidad del entregable |

## 14. Referencias

1. Ley 1273 de 2009, texto compilado. Senado de la República de Colombia.
   <http://www.secretariasenado.gov.co/senado/basedoc/ley_1273_2009.html>
2. PAe. *MAGERIT v3 — Metodología de Análisis y Gestión de Riesgos de los
   Sistemas de Información*.
   <https://administracionelectronica.gob.es/pae_Home/pae_Documentacion/pae_Metodolog/pae_Magerit.html>
3. ISO/IEC 27001:2022. *Information security, cybersecurity and privacy
   protection — Information security management systems — Requirements*.
   <https://www.iso.org/standard/27001>
4. OWASP Foundation. *OWASP Top 10*. <https://owasp.org/www-project-top-ten/>
5. Scapy. *Documentation*. <https://scapy.readthedocs.io/>
6. RFC 8446. *The Transport Layer Security (TLS) Protocol Version 1.3*.
7. Ley 1581 de 2012, protección de datos personales (Colombia).

## 15. Anexos

| Anexo | Contenido |
|---|---|
| A | [`demo-http-vs-https.md`](./demo-http-vs-https.md) — guion reproducible de la comparación |
| B | [`evidencias.md`](./evidencias.md) — checklist con comandos y resultados |
| C | [`magerit-v3.md`](./magerit-v3.md) — análisis de riesgos completo |
| D | [`iso-27001-2022.md`](./iso-27001-2022.md) — tabla control → evidencia → brecha |
| E | [`ley-1273-2009.md`](./ley-1273-2009.md) — análisis del artículo 269C |
| F | `evidencias/01-laboratorio-100-nodos.png` y `evidencias/02-render-fps.png` |

## Lista de verificación antes de entregar

- [ ] Completar nombre, curso, docente y fecha de la portada.
- [ ] Confirmar si el docente exige captura real: si sí, ejecutar el guion de
      Npcap en un equipo con permisos de administrador y sustituir las cifras
      `synthetic: true` por las reales.
- [ ] Si se exige 30 FPS en pantalla, repetir la medición en una sesión
      interactiva y actualizar E6 de `evidencias.md`.
- [ ] Revisar que las capturas no muestren datos personales reales.
- [ ] Exportar a PDF con las imágenes incrustadas.
