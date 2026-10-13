# Sala servidor web

## Documento de continuidad para Codex

Fecha: 16 de agosto de 2026.

Este documento deja los antecedentes técnicos y criterios de construcción para evolucionar **Desafío / Millonario educativo V3.1.4** desde su sala participativa exclusivamente local hacia una arquitectura con **dos modalidades de conectividad**:

1. **Sala Local** — funcionamiento actual sobre la misma red LAN/Wi-Fi.
2. **Sala Internet** — funcionamiento mediante Internet, permitiendo que cada teléfono participe desde cualquier Wi-Fi, 4G o 5G.

La intención no es reemplazar la arquitectura actual. La Sala Internet debe agregarse como una segunda modalidad y reutilizar el mismo motor, API, WebSocket y cliente móvil existentes.

---

## 1. Estado actual comprobado

La versión de referencia es **V3.1.4**, ubicada en `v3_1/`.

La aplicación ya contiene gran parte de la arquitectura necesaria:

- PySide6 / QML como aplicación anfitriona audiovisual.
- FastAPI como servidor HTTP local.
- Uvicorn como servidor ASGI.
- WebSocket para eventos en tiempo real.
- Cliente móvil HTML/CSS/JavaScript en `v3_1/mobile/`.
- Tokens individuales por participante.
- Reconexión automática.
- Heartbeat.
- Control de respuestas duplicadas y tardías.
- Persistencia local de sesión/eventos.
- QR de acceso a la sala.
- Límite oficial actual validado: 30 participantes.

Dependencias relevantes actuales en `v3_1/pyproject.toml`:

- `fastapi`
- `uvicorn`
- `websockets`
- `segno`

El servicio actual está implementado principalmente en:

- `v3_1/src/millonario_v3/participation/service.py`
- `v3_1/src/millonario_v3/participation/api.py`
- `v3_1/src/millonario_v3/participation/network.py`
- `v3_1/src/millonario_v3/participation/room.py`
- `v3_1/src/millonario_v3/participative_controller.py`
- `v3_1/mobile/app.js`

La V3.1.4 levanta Uvicorn sobre `0.0.0.0` y selecciona normalmente el puerto 8787. La URL actual se construye con la IP LAN del notebook:

```text
http://IP-DEL-LAPTOP:PUERTO/
```

El QR actual apunta a esa URL local.

---

## 2. Aclaración arquitectónica importante

### Sala Local

La Sala Local **no requiere un router propio**.

El notebook anfitrión y los teléfonos solamente deben encontrarse en la **misma red LAN/Wi-Fi** y dicha red debe permitir tráfico directo entre clientes.

Ejemplo:

```text
Wi-Fi del recinto
       |
   +---+---+
   |       |
Notebook  Telefonos
   |
FastAPI :8787
```

Puede funcionar sin acceso a Internet.

Un router portátil puede utilizarse voluntariamente para crear una red privada cuando sea conveniente, pero **no es una dependencia de la Sala Local**.

Algunas redes de invitados implementan `client isolation`; en ese caso los dispositivos pueden tener Internet pero no comunicarse entre sí. Ese escenario es precisamente uno de los motivos para incorporar Sala Internet.

---

## 3. Objetivo de Sala Internet

Permitir que el juego continúe ejecutándose físicamente en el notebook anfitrión, pero que el servidor local pueda ser alcanzado desde Internet mediante una URL pública temporal segura.

Arquitectura objetivo inicial:

```text
Telefonos de participantes
Wi-Fi / 4G / 5G
        |
        v
      Internet
        |
        v
URL publica HTTPS
        |
        v
Tunel seguro
        |
        v
localhost / 127.0.0.1:8787
        |
        v
FastAPI + Uvicorn
        |
        v
Motor actual de Millonario V3.1.4
```

El backend principal debe seguir ejecutándose localmente. En esta etapa **no es necesario migrar el motor del juego a Vercel, Render, VPS, Supabase u otro backend cloud**.

---

## 4. Decisión de diseño: dos modalidades explícitas

La interfaz de creación de sala debe evolucionar hacia una selección explícita, por ejemplo:

```text
CREAR NUEVA SALA

[ Sala Local ]
Misma red LAN/Wi-Fi.
Puede funcionar sin Internet.

[ Sala Internet ]
Participantes desde cualquier Wi-Fi, 4G o 5G.
Requiere Internet en el notebook anfitrión.
```

No intentar detectar automáticamente qué modalidad desea el usuario.

La separación debe ser visible y comprensible.

### Principio de compatibilidad

**Sala Local debe conservar el comportamiento actual de V3.1.4.**

Agregar Sala Internet no debe degradar, reemplazar ni hacer depender de Internet a la Sala Local.

---

## 5. Ventaja importante del cliente móvil existente

El cliente móvil ya utiliza rutas relativas para la API:

```javascript
const apiBase = "/api/v1";
```

Además, el WebSocket se construye según el origen desde el cual fue cargada la página:

```javascript
const protocol = location.protocol === "https:" ? "wss:" : "ws:";
return `${protocol}//${location.host}/ws/v1/room?...`;
```

Esto permite que el mismo cliente funcione en ambos modos:

### Local

```text
http://192.168.x.x:8787
ws://192.168.x.x:8787/ws/v1/room
```

### Internet

```text
https://URL-PUBLICA
wss://URL-PUBLICA/ws/v1/room
```

Por lo tanto, **no crear dos clientes móviles distintos** salvo que una necesidad técnica posterior lo justifique.

---

## 6. Túnel público propuesto para primera implementación

Para una primera V3.2 / prototipo de Sala Internet se propone utilizar **Cloudflare Tunnel**, inicialmente mediante una URL temporal de prueba.

Conceptualmente:

```text
cloudflared tunnel --url http://localhost:8787
```

El proceso entrega una URL pública HTTPS temporal.

Ejemplo conceptual:

```text
https://xxxxx.trycloudflare.com
```

Esa URL debe ser capturada por la aplicación y utilizada para:

- mostrar la dirección pública;
- generar el QR de Sala Internet;
- validar salud del túnel;
- permitir acceso HTTP/HTTPS;
- permitir WebSocket seguro WSS.

### Importante

No incorporar todavía un dominio permanente como requisito de la primera versión.

La primera meta es comprobar el flujo completo con URL temporal.

El diseño debe intentar encapsular el proveedor de túnel para que en el futuro pueda sustituirse sin modificar el motor del juego.

---

## 7. Cambio mínimo requerido en el QR

Actualmente `ParticipationService.start()` genera una URL basada en la IP LAN y esa URL se pasa directamente al QR.

Hoy:

```text
Sala Local
    |
http://192.168.x.x:8787
    |
QR
```

Sala Internet debe hacer:

```text
FastAPI :8787
    |
Tunel
    |
https://URL-PUBLICA
    |
QR
```

Conviene separar conceptualmente:

```text
internal_url
local_url
public_url
participant_url
```

El QR debe construirse siempre desde `participant_url`.

En modo local:

```text
participant_url = local_url
```

En modo Internet:

```text
participant_url = public_url
```

Evitar que otras partes del juego dependan directamente de la IP LAN.

---

## 8. Propuesta de componentes

Una estructura posible sin reescribir la aplicación:

```text
participation/
    api.py
    models.py
    network.py
    qr.py
    room.py
    service.py
    tunnel.py          <- nuevo
```

### `network.py`

Mantener responsabilidades LAN:

- detectar IP local;
- encontrar puerto disponible;
- construir URL local.

### `tunnel.py`

Nueva responsabilidad exclusiva de Internet:

- detectar disponibilidad de `cloudflared`;
- iniciar el proceso del túnel;
- capturar URL pública;
- verificar que el proceso siga vivo;
- cerrar el proceso al cerrar Sala Internet;
- devolver errores claros;
- evitar procesos huérfanos.

### `service.py`

Debe coordinar:

```text
start_local(...)
start_internet(...)
stop(...)
```

No es obligatorio usar exactamente estos nombres; lo importante es separar responsabilidades.

---

## 9. Secuencia esperada de Sala Internet

Flujo objetivo del anfitrión:

```text
1. Usuario elige Sala Internet.
2. Iniciar servidor local FastAPI/Uvicorn.
3. Verificar que /health responde localmente.
4. Verificar conectividad a Internet.
5. Iniciar túnel hacia localhost:puerto.
6. Obtener URL HTTPS pública.
7. Verificar acceso a /health mediante la URL pública.
8. Generar QR con URL pública.
9. Mostrar sala lista.
10. Participantes escanean QR desde cualquier conexión.
11. API y WebSocket operan normalmente.
12. Al cerrar sala, detener túnel y servidor de forma ordenada.
```

Durante la preparación puede mostrarse estado progresivo:

```text
Preparando Sala Internet...

[OK] Servidor local iniciado
[OK] Conexion a Internet
[OK] Tunel seguro activo
[OK] URL publica disponible
[OK] QR generado

Sala lista
```

Si cualquier paso falla, explicar cuál falló y permitir volver al menú sin dejar procesos abiertos.

---

## 10. Seguridad antes de exposición pública

La arquitectura LAN actual fue diseñada para una red privada. Antes de declarar Sala Internet estable, auditar específicamente:

- endpoints HTTP expuestos;
- operaciones que requieren token;
- posibilidad de ejecutar acciones de anfitrión desde Internet;
- datos privados incluidos en snapshots;
- capacidad de enumerar participantes;
- generación y fortaleza de tokens;
- reingreso desde un dispositivo registrado;
- rate limiting básico de `join` y respuestas si resulta necesario;
- tamaño máximo de mensajes WebSocket;
- manejo de payloads inválidos;
- cierre de conexiones antiguas;
- logs que puedan incluir tokens.

### Código de sala

En V3.1.4 el código de cuatro dígitos ya no protege realmente la ruta; funciona principalmente como referencia visual porque cada ejecutable aloja una sola sala activa.

Para Sala Internet considerar una protección adicional de enrolamiento.

Alternativas para evaluar:

1. PIN/código de evento requerido al ingresar.
2. Token secreto incorporado al QR.
3. URL pública temporal suficientemente aleatoria + límite de cupo, solo para prototipo.

Para la primera prueba controlada se puede mantener una solución sencilla, pero **no asumir que una URL pública permanente puede quedar abierta sin protección adicional**.

---

## 11. Capacidad de participantes

V3.1.4 está validada oficialmente para **30 participantes**.

No asumir que cambiar `max_participants=30` a `120` equivale a validar 120 usuarios.

La arquitectura FastAPI/WebSocket probablemente puede manejar más conexiones que el límite actual, pero debe comprobarse empíricamente.

Plan de pruebas sugerido:

```text
30 conexiones  -> baseline existente
60 conexiones  -> validar
100 conexiones -> validar
120 conexiones -> objetivo
```

Medir al menos:

- conexiones WebSocket activas;
- latencia de apertura de pulsadores;
- latencia de respuestas;
- ráfaga simultánea de respuestas;
- CPU;
- memoria;
- reconexiones;
- pérdida de mensajes;
- orden de llegada;
- cierre de votación bajo carga.

No utilizar 120 participantes en una actividad formal hasta completar la prueba correspondiente.

---

## 12. Consideración sobre latencia y justicia

Al pasar de LAN a Internet aparecerá una dispersión de latencia mayor entre participantes.

Para preguntas clasificatorias donde el orden de respuesta importa:

- mantener al servidor como autoridad temporal;
- registrar la hora de recepción en servidor;
- no confiar en timestamps enviados por el teléfono;
- estudiar tolerancias si diferencias de pocos milisegundos pasan a ser relevantes;
- probar conexiones reales mezclando Wi-Fi, 4G y 5G.

El cliente puede mostrar un cronómetro visual, pero el cierre efectivo debe seguir siendo responsabilidad del servidor.

---

## 13. Resiliencia

### Sala Local

Debe continuar funcionando aunque no haya Internet.

### Sala Internet

Debe detectar si:

- se pierde Internet;
- cae el proceso del túnel;
- cambia la conectividad del notebook;
- la URL pública deja de responder.

En esos casos:

- no cerrar abruptamente la aplicación anfitriona;
- conservar el estado del juego cuando sea posible;
- informar claramente que la conectividad externa se perdió;
- permitir terminar/cerrar la sala de manera segura;
- evaluar posteriormente una opción de retorno a Sala Local.

No intentar implementar failover automático complejo en la primera iteración.

---

## 14. Empaquetado portable

La V3.1.4 se distribuye como aplicación portable compilada.

Sala Internet debe conservar ese principio.

Evaluar dos estrategias para `cloudflared`:

### A. Binario incorporado

Ventaja: experiencia de un clic.

Desventaja: aumenta paquete y obliga a mantener el binario actualizado.

### B. Dependencia externa detectada

Ventaja: paquete principal más limpio.

Desventaja: configuración manual adicional.

Para el prototipo de desarrollo puede utilizarse instalación externa. Antes de distribuir una V3.2 portable decidir cuál alternativa ofrece mejor experiencia y mantenimiento.

No descargar binarios silenciosamente en tiempo de ejecución sin una decisión explícita del proyecto.

---

## 15. Pruebas obligatorias

Antes de modificar:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\v3_1\tests
```

Después de cada bloque relevante repetir las pruebas existentes.

Agregar pruebas nuevas para:

- selección Local / Internet;
- URL participante correcta por modalidad;
- QR local;
- QR público;
- arranque y parada del túnel mediante mocks/fakes;
- error al no existir `cloudflared`;
- error de Internet;
- caída del túnel;
- cierre limpio sin proceso huérfano;
- compatibilidad de WebSocket con origen HTTPS/WSS;
- regresión completa de Sala Local.

La prueba final debe incluir al menos dos teléfonos reales en redes distintas:

```text
Notebook -> Internet
Telefono A -> Wi-Fi distinto
Telefono B -> 4G/5G
```

Ambos deben:

- abrir el QR;
- enrolarse;
- recibir WebSocket;
- responder;
- reconectarse después de recargar;
- participar en consulta con el público.

---

## 16. No modificar V2

La V2 estable debe permanecer intacta.

La evolución debe realizarse sobre `v3_1/` o, si Codex determina que corresponde formalizar una nueva versión, crear una carpeta/versionado V3.2 sin destruir la V3.1.4 estable.

No sobrescribir un ejecutable estable antes de completar pruebas y build portable.

---

## 17. Alcance recomendado para la primera iteración

### Sí construir

- selector Sala Local / Sala Internet;
- abstracción de URL participante;
- `TunnelService` o equivalente;
- soporte inicial de Cloudflare Tunnel;
- captura de URL pública;
- QR basado en URL pública;
- estado visual de preparación;
- cierre limpio del túnel;
- pruebas automatizadas de regresión;
- prueba manual Internet real.

### No construir todavía

- dominio propio permanente;
- backend cloud independiente;
- base de datos remota;
- cuentas de usuario;
- panel administrativo web remoto;
- múltiples salas simultáneas en un solo ejecutable;
- balanceo de carga;
- failover automático LAN/Internet;
- escalado horizontal.

Mantener esta iteración pequeña y verificable.

---

## 18. Arquitectura deseada al cierre de la iteración

```text
                 MOTOR DE JUEGO V3.x
                        |
                 FastAPI + WebSocket
                        |
              +---------+---------+
              |                   |
          SALA LOCAL          SALA INTERNET
              |                   |
        IP LAN + HTTP       Tunnel + HTTPS
        WS local            WSS publico
              |                   |
         QR local             QR publico
              |                   |
     misma LAN/Wi-Fi       cualquier Internet
```

El motor, la sala, los participantes, los tokens, los eventos y el cliente móvil deben ser esencialmente los mismos.

La diferencia entre las modalidades debe concentrarse en la **capa de transporte y descubrimiento de la URL**, no en la lógica del juego.

---

## 19. Criterios de aceptación iniciales

La primera implementación de Sala Internet puede considerarse exitosa cuando:

1. Sala Local continúa funcionando exactamente como antes.
2. El anfitrión puede elegir Sala Internet desde la interfaz.
3. El juego levanta el servidor local.
4. Se crea un túnel público temporal.
5. La URL pública HTTPS se detecta automáticamente.
6. El QR contiene esa URL pública.
7. Un teléfono fuera de la LAN puede enrolarse.
8. El WebSocket funciona mediante WSS.
9. Las respuestas llegan al mismo `RoomManager` actual.
10. Reconexión y heartbeat continúan funcionando.
11. Al cerrar la sala no queda `cloudflared` ejecutándose.
12. Las pruebas existentes de V3.1.4 continúan pasando.

---

## 20. Principio rector para Codex

**No reconstruir una aplicación web nueva si no es necesario.**

La V3.1.4 ya posee servidor, API, WebSocket, cliente móvil, estado de sala y lógica participativa.

El siguiente paso debe ser principalmente:

```text
servidor local existente
        +
segunda modalidad de transporte
        +
URL publica temporal
        +
QR publico
        +
seguridad y pruebas
```

Preservar la arquitectura que ya funciona y ampliar únicamente los puntos necesarios.
