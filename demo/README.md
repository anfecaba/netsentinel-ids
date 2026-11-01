# Demo HTTP vs HTTPS del laboratorio

Dos servidores mínimos que sirven el **mismo formulario** de login: uno por HTTP
en claro (`:8080`) y otro por HTTPS con certificado autofirmado (`:8443`). El
objetivo es comparar qué observa la captura pasiva de NetSentinel en cada caso.

> **Datos sintéticos.** `alice` / `SuperSecret123` no son una cuenta real.
> Este formulario existe solo para el laboratorio académico.

## Qué hace y qué no hace

| Hace | No hace |
|---|---|
| Sirve `login.html` y procesa `POST /login` | No valida contra ninguna base de datos |
| Responde 200 si llegan `username` y `password` | No registra los valores recibidos |
| Puede ir envuelto en TLS (`:8443`) | No persiste nada en disco |
| Devuelve `400` si faltan campos | No acepta otros métodos ni rutas |

El log de consola solo imprime método, ruta y código de estado. El cuerpo de la
petición se lee para consumirlo y se descarta.

## Requisitos

- El Python del entorno de captura (`capture/.venv`), que ya incluye `cryptography`
  en el extra `demo`.
- Si aún no lo instalaste:

```powershell
cd capture
uv sync --extra dev --extra demo
```

## Arrancar los servidores

Windows (PowerShell), desde `demo/`:

```powershell
..\capture\.venv\Scripts\python.exe http_login_server.py
..\capture\.venv\Scripts\python.exe generate_cert.py
..\capture\.venv\Scripts\python.exe https_login_server.py
```

Linux/macOS, desde `demo/`:

```bash
../capture/.venv/bin/python http_login_server.py
../capture/.venv/bin/python generate_cert.py
../capture/.venv/bin/python https_login_server.py
```

También funciona con `uv run --project ../capture python <script>` si prefieres
que `uv` resuelva el intérprete.

Salida esperada:

```
[demo] HTTP  http://127.0.0.1:8080/
[demo] HTTPS https://127.0.0.1:8443/
[demo] Certificado autofirmado: el navegador pedirá aceptarlo (esperado).
```

## Verificar sin navegador

```powershell
curl.exe -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8080/login -d "username=alice&password=SuperSecret123"
curl.exe -k -s -o NUL -w "%{http_code}" -X POST https://127.0.0.1:8443/login -d "username=alice&password=SuperSecret123"
```

Ambos deben devolver `200`. Sin `-k`, el segundo falla con un error de
certificado: es la prueba de que el certificado es autofirmado.

## Advertencia del navegador

Al abrir `https://127.0.0.1:8443/` el navegador mostrará
«La conexión no es privada» o similar, porque el certificado lo firmó el propio
laboratorio y no una CA pública.

- Chrome/Edge: **Configuración avanzada → Continuar a 127.0.0.1 (no seguro)**.
- Firefox: **Avanzado → Aceptar el riesgo y continuar**.

Aceptar ese aviso **no** forma parte del experimento: el punto es que, aun con
la conexión aceptada, la captura pasiva no puede leer el cuerpo del POST.

## Guion de la comparación

1. Arranca la captura pasiva (ver `capture/README.md`) con autorización.
2. Abre `http://127.0.0.1:8080/`, pulsa **Iniciar sesión** y observa en
   `/laboratorio` la credencial con los valores completos y el nodo en rojo.
3. Abre `https://127.0.0.1:8443/`, acepta el aviso y pulsa **Iniciar sesión**.
   Verás un flujo `HTTPS` cifrado con su nota de metadatos, y **ninguna**
   credencial nueva.
4. Compara ambas evidencias con `docs/visual-mitm/demo-http-vs-https.md`.

## Archivos

```
demo/
├── common.py             handler compartido (rutas, respuestas, log sin cuerpo)
├── http_login_server.py  :8080 sin cifrar
├── https_login_server.py :8443 con TLS
├── generate_cert.py      certificado autofirmado en certs/
├── login.html            formulario idéntico para ambos esquemas
└── certs/                generado; ignorado por git
```
