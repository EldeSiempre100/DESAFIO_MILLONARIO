# V4 — Nueva rama · Versión online

## Documento de arquitectura y continuidad para Codex

Fecha: 17 de agosto de 2026.

## 0. Propósito

Este documento define la **V4 online** de Desafío / Millonario educativo como una evolución separada de la V3.1.4 estable.

La V4 no reemplaza la versión de escritorio ni la futura modalidad Internet por túnel. Se plantea como una **rama nueva**, destinada a construir una versión web/cloud que pueda vivir permanentemente en Internet y ejecutarse desde navegador.

### Regla de continuidad

- **No modificar ni degradar V3.1.4 estable.**
- Crear una rama independiente para V4, sugerida: `v4-online` o `web-v1`.
- Reutilizar el mayor número posible de componentes del motor actual.
- Portar la interfaz anfitriona a web sin reescribir innecesariamente la lógica ya validada.

---

# 1. Las tres arquitecturas del proyecto

La evolución del proyecto debe entenderse como tres modos hermanos sobre un mismo núcleo funcional.

```text
                     CORE MILLONARIO
                preguntas / reglas / juego
                         │
           ┌─────────────┼─────────────┐
           │             │             │
           ▼             ▼             ▼
      DESKTOP        INTERNET         WEB
       LOCAL          TÚNEL          CLOUD
           │             │             │
        laptop         laptop         Render
           │             │             │
     misma Wi-Fi     4G/5G/Wi-Fi    4G/5G/Wi-Fi
```

## 1.1 Sala Local

La laptop ejecuta el servidor y los teléfonos se conectan desde la misma red LAN/Wi-Fi.

No requiere Internet.

## 1.2 Sala Internet por túnel

La laptop sigue ejecutando el servidor, pero un túnel seguro publica temporalmente el servicio hacia Internet.

Los jugadores pueden usar cualquier Wi-Fi, 4G o 5G.

## 1.3 V4 Online / Cloud

El servidor ya no corre en la laptop anfitriona.

El backend vive permanentemente en infraestructura cloud.

La aplicación puede abrirse desde cualquier navegador y mantenerse disponible aunque el computador original esté apagado.

---

# 2. Objetivo funcional de V4

La V4 debe permitir que el anfitrión ingrese desde navegador a una aplicación web, seleccione o edite un banco de preguntas, cree una partida y entregue a los jugadores un QR o código de sala.

Ejemplo conceptual:

```text
DESAFÍO MILLONARIO

[ Crear partida ]

Mis bancos
────────────────
Fondos Mutuos
APV
Economía
Mercados

[ Editar ]
[ Importar Excel ]
```

Al crear una partida:

```text
Sala 7492

████████
██ QR ██
████████

0 / 120 participantes

[ Iniciar ]
```

Los participantes ingresan desde sus teléfonos sin instalar aplicaciones.

---

# 3. Arquitectura objetivo inicial

La primera arquitectura recomendada para V4 es mantener **Python + FastAPI + WebSocket**, porque ya forman parte de V3.1.4 y existe lógica validada que puede reutilizarse.

```text
                 DESAFÍO MILLONARIO WEB

                         INTERNET
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
       PRESENTADOR                    JUGADORES
       navegador                     navegador
       /admin                        /jugar
             │                             │
             └──────── HTTPS/WSS ─────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  BACKEND CLOUD   │
                  │                  │
                  │ FastAPI          │
                  │ Uvicorn          │
                  │ WebSockets       │
                  │ motor del juego  │
                  └────────┬─────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │             │
                    │ preguntas   │
                    │ bancos      │
                    │ partidas    │
                    │ resultados  │
                    └─────────────┘
```

## Plataforma inicial sugerida

Para una primera V4, evaluar **Render** como opción principal porque la arquitectura actual ya funciona como un servidor Python tradicional con FastAPI/Uvicorn/WebSockets.

Vercel puede evaluarse posteriormente, especialmente si se adopta una arquitectura más distribuida/serverless, pero no debe forzarse una migración de paradigma antes de validar la V4.

Codex debe verificar las capacidades y condiciones actuales del proveedor elegido antes de desplegar.

---

# 4. Qué se puede reutilizar de V3.1.4

La intención es evitar una reescritura completa.

## Reutilizable o adaptable directamente

```text
✅ modelos Question / Project
✅ validaciones
✅ importador Excel
✅ lógica de rondas
✅ puntuación
✅ clasificación
✅ RoomManager
✅ API FastAPI
✅ WebSockets
✅ tokens
✅ reconexión
✅ heartbeat
✅ lógica A-D
✅ cliente móvil HTML/JS
✅ reglas de control de respuestas duplicadas/tardías
```

Archivos de referencia actuales:

- `v3_1/src/millonario_v3/model.py`
- `v3_1/src/millonario_v3/excel_import.py`
- `v3_1/src/millonario_v3/engine.py`
- `v3_1/src/millonario_v3/rounds.py`
- `v3_1/src/millonario_v3/participation/room.py`
- `v3_1/src/millonario_v3/participation/api.py`
- `v3_1/src/millonario_v3/participation/service.py`
- `v3_1/mobile/`

---

# 5. Qué debe reconstruirse para web

La principal pieza que **no se traslada directamente** es la interfaz anfitriona PySide6/QML.

```text
❌ PySide6 / QML no se convierte automáticamente en una página web.
```

Debe reconstruirse en HTML/CSS/JavaScript o en un framework web apropiado.

Pantallas a portar:

- Menú principal.
- Lobby.
- Pregunta clasificatoria.
- Apertura/cierre de votación.
- Resultados.
- Selección de participantes.
- Rondas.
- Ranking.
- Comodines.
- Cierre de partida.
- Editor de preguntas.
- Importador Excel.

La prioridad es conservar la lógica, no copiar literalmente la implementación QML.

---

# 6. Persistencia: cambio fundamental respecto de Desktop

La versión de escritorio puede utilizar archivos locales como:

```text
demo.juego
demo.history.json
sessions/
```

La V4 cloud no debe depender del filesystem local del servidor como fuente de verdad.

La persistencia debe migrarse a una base de datos.

Arquitectura propuesta:

```text
PostgreSQL

question_banks
questions
games
participants
answers
results
sessions
```

## Posible estructura mínima

### `question_banks`

- id
- name
- description
- created_at
- updated_at

### `questions`

- id
- bank_id
- prompt
- answer_a
- answer_b
- answer_c
- answer_d
- correct_index
- active
- order/index opcional

### `games`

- id
- room_code
- bank_id
- status
- created_at
- started_at
- finished_at

### `participants`

- id
- game_id
- alias
- avatar
- token/identity reference
- role
- connected/status

### `answers`

- id
- game_id
- participant_id
- question/opening_id
- answer
- correct
- server_received_at
- response_time_ms

### `results`

- game_id
- participant_id
- score
- position
- metadata

El esquema final debe definirse después de revisar las necesidades reales del motor actual.

---

# 7. Editor web de preguntas

La V4 debe conservar la posibilidad de editar preguntas desde la aplicación.

Ruta conceptual:

```text
/admin/preguntas
```

Ejemplo:

```text
Pregunta 7

¿Cuál es la actual TPM en Chile?

A) 3,0%
B) 4,0%
C) 4,5% ✓
D) 6,0%

[ Guardar ]
```

El editor debe permitir como mínimo:

- crear pregunta;
- editar pregunta;
- eliminar/desactivar pregunta;
- definir alternativa correcta;
- asociarla a un banco;
- ordenar preguntas si corresponde;
- validar longitudes y duplicados según las reglas existentes.

---

# 8. Importación Excel en V4

La carga mediante Excel debe mantenerse como función prioritaria.

El importador actual ya contiene validación del `.xlsx`, incluyendo:

- extensión válida;
- hoja `Preguntas`;
- columnas obligatorias;
- texto de pregunta;
- cuatro alternativas;
- respuesta correcta A–D;
- columna `Activa`;
- detección de duplicados;
- rechazo de archivos dañados;
- límites actualmente definidos para el banco.

La V4 debe reutilizar esa lógica o extraerla a un módulo compartido.

Flujo objetivo:

```text
/admin
   ↓
SUBIR EXCEL
   ↓
Banco_preguntas.xlsx
   ↓
FastAPI recibe archivo
   ↓
validador Excel existente/adaptado
   ↓
PostgreSQL
   ↓
Banco disponible para jugar
```

## Uso recomendado

```text
Una pregunta
      ↓
editor web

muchas preguntas
      ↓
Excel
```

La aplicación también debería mantener una opción para **descargar la plantilla oficial Excel**.

---

# 9. Bancos múltiples

A diferencia de la versión local, V4 debe contemplar naturalmente varios bancos de preguntas.

Ejemplo:

```text
MIS BANCOS

○ Fondos Mutuos
  12 preguntas

○ Mercado y economía
  12 preguntas

○ APV
  12 preguntas

○ Riesgo
  12 preguntas
```

El anfitrión selecciona un banco antes de crear una partida.

Esto convierte al sistema en una plataforma reutilizable y no en un único juego cerrado.

---

# 10. Roles web

Se deben separar al menos tres experiencias.

## 10.1 Administrador / editor

```text
/admin
```

Funciones:

- administrar bancos;
- editar preguntas;
- importar Excel;
- crear partidas;
- revisar partidas anteriores;
- configuración general.

## 10.2 Anfitrión / presenter

```text
/host/{game}
```

Funciones:

- ver lobby;
- iniciar clasificación;
- controlar timing;
- abrir/cerrar votaciones;
- seleccionar participantes;
- avanzar preguntas;
- usar comodines;
- mostrar resultados/ranking;
- finalizar/repetir partida.

## 10.3 Jugador

```text
/join/{room}
```

o entrada mediante código/QR.

Funciones:

- enrolarse;
- elegir alias/avatar;
- reconectarse;
- responder A–D cuando corresponda;
- ver estados de espera;
- recibir eventos en tiempo real.

---

# 11. Sala y QR

En V4 el servidor es permanente, pero las **salas son temporales**.

Ejemplo:

```text
Servidor permanente
https://desafiomillonario.example
          │
          ├── Sala 7492
          ├── Sala 1835
          └── Sala 4201
```

Cada partida debe tener:

- identificador interno;
- código corto de sala;
- URL pública;
- QR;
- estado `open / locked / playing / finished` o equivalente;
- banco de preguntas asociado;
- anfitrión autorizado.

La V4 debe poder evolucionar a **múltiples salas simultáneas**. No asumir para siempre el modelo V3.1.4 de una única sala por ejecutable.

---

# 12. Seguridad mínima

Al vivir permanentemente en Internet, V4 requiere una capa de seguridad superior a la sala LAN.

Como mínimo:

- autenticación de administrador/anfitrión;
- autorización para editar bancos;
- códigos de sala no predecibles o con protección suficiente;
- tokens de participante;
- rate limiting en enrolamiento y endpoints sensibles;
- validación de archivos Excel;
- límites de tamaño de upload;
- protección contra ejecución o lectura arbitraria de archivos;
- sanitización/escape de contenido mostrado en HTML;
- secretos fuera del repositorio mediante variables de entorno;
- separación clara entre endpoints públicos y administrativos.

No incorporar credenciales en el código.

---

# 13. Estado distribuido y WebSockets

La V3.1.4 mantiene el estado de una sala en memoria porque existe un único proceso local.

En V4 esto puede funcionar inicialmente si se garantiza una única instancia del backend, pero no debe convertirse en una dependencia estructural difícil de escalar.

Codex debe preparar una abstracción clara para:

- estado persistente de partida;
- presencia de participantes;
- reconexión;
- publicación de eventos;
- coordinación entre instancias si el hosting escala horizontalmente.

Una evolución posterior puede requerir Redis/pub-sub u otro mecanismo equivalente.

Para V4 inicial, preferir simplicidad y consistencia sobre escalado prematuro.

---

# 14. Capacidad

La V3.1.4 tiene un límite oficial validado de 30 participantes.

V4 debe diseñarse para superar este límite, pero **no declarar 120 participantes como soportados hasta probarlo**.

Secuencia recomendada de validación:

```text
30
 ↓
60
 ↓
100
 ↓
120
```

Pruebas necesarias:

- enrolamiento concurrente;
- WebSockets concurrentes;
- ráfaga simultánea de respuestas;
- latencia de recepción;
- orden de llegada al servidor;
- reconexión;
- caída temporal de red móvil;
- cliente en segundo plano;
- cierre de votación;
- rechazo de respuestas tardías;
- consumo de CPU/RAM;
- persistencia de resultados.

El tiempo oficial debe seguir controlado por servidor.

---

# 15. Estrategia de desarrollo recomendada

No intentar construir toda la V4 en una sola intervención.

## Fase 0 — Preparación

- Crear rama `v4-online`.
- Congelar V3.1.4 como referencia estable.
- Documentar módulos reutilizables.
- Ejecutar suite de pruebas actual antes de extraer código.

## Fase 1 — Core reutilizable

- Separar lógica independiente de Qt/QML.
- Confirmar que modelo, rondas, importador y RoomManager pueden usarse sin GUI Desktop.
- Mantener pruebas unitarias.

## Fase 2 — Backend cloud mínimo

- Levantar FastAPI independiente.
- Implementar health check.
- Crear una sala web.
- Permitir join.
- WebSocket.
- Respuesta A–D.
- Reconexión.

## Fase 3 — Persistencia

- Incorporar PostgreSQL.
- Bancos.
- Preguntas.
- Partidas.
- Participantes.
- Respuestas.

## Fase 4 — Panel anfitrión web

- Lobby.
- Clasificación.
- Resultados.
- Selección.
- Rondas.
- Comodines.
- Final.

## Fase 5 — Editor + Excel

- CRUD de bancos.
- CRUD de preguntas.
- Upload `.xlsx`.
- Validación existente.
- Preview antes de importar si resulta conveniente.
- Descarga de plantilla.

## Fase 6 — Deploy

- Despliegue inicial en Render u otro proveedor seleccionado.
- Variables de entorno.
- HTTPS/WSS.
- Base persistente.
- Logs.

## Fase 7 — Prueba de carga

- 30.
- 60.
- 100.
- 120.

## Fase 8 — Endurecimiento

- autenticación;
- rate limiting;
- observabilidad;
- recuperación ante reinicio;
- backups de base;
- pruebas de seguridad básicas.

---

# 16. Relación con la futura V3.2 por túnel

La V3.2 Sala Internet por túnel no es trabajo descartable.

Debe utilizarse para validar:

- comportamiento real de WebSockets fuera de LAN;
- latencia móvil;
- reconexión;
- clientes 4G/5G;
- manejo de pérdidas de red;
- concurrencia.

Esos hallazgos deben retroalimentar V4.

Ruta recomendada:

```text
V3.1.4 estable
     ↓
V3.2
Sala Local + Sala Internet/Tunnel
     ↓
validar comportamiento Internet
     ↓
V4 rama online
     ↓
FastAPI cloud
     ↓
PostgreSQL
     ↓
panel anfitrión web
     ↓
editor + importador Excel
     ↓
deploy permanente
```

---

# 17. Criterio de éxito de V4 inicial

La primera V4 debe considerarse funcional cuando un usuario pueda:

1. abrir la plataforma desde navegador;
2. autenticarse como anfitrión/administrador;
3. crear o seleccionar un banco de preguntas;
4. importar el banco desde el Excel oficial;
5. editar preguntas desde web;
6. crear una sala;
7. obtener código y QR;
8. enrolar teléfonos desde redes distintas;
9. ejecutar clasificación;
10. recibir respuestas en tiempo real;
11. seleccionar participantes;
12. ejecutar las rondas del juego;
13. usar los comodines relevantes;
14. terminar la partida;
15. conservar resultados y banco de preguntas en base de datos;
16. repetir o crear una nueva partida sin depender de la laptop original.

---

# 18. Principio arquitectónico final

V4 no debe convertirse en una reescritura total del proyecto.

La meta es transformar:

```text
Aplicación Desktop con servidor participativo incorporado
```

en:

```text
Motor de juego reutilizable
        │
        ├── Desktop Local
        ├── Desktop + Internet Tunnel
        └── Web Cloud V4
```

El valor acumulado de V3.1.4 debe conservarse.

La V4 debe ser una **nueva superficie de ejecución del mismo producto**, no un proyecto desconectado que duplique reglas, validaciones y comportamiento.

---

# 19. Instrucción inicial sugerida para Codex

> Lee `V4_NUEVA_RAMA_VERSION_ONLINE.md`, revisa V3.1.4 como referencia estable y prepara la rama `v4-online`. No modifiques la versión estable. Primero identifica y documenta qué módulos pueden extraerse/reutilizarse sin dependencia de PySide6/QML. Luego construye una V4 web por etapas, comenzando por un backend FastAPI mínimo con una sala, join, WebSocket y respuesta A–D. Mantén la importación Excel y el editor de preguntas como requisitos de producto. No declares soporte de 120 participantes hasta realizar pruebas de carga.
