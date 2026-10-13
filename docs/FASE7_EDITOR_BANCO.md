# Fase 7 — Editor de preguntas y Excel

Estado: **7A IMPLEMENTADA · 7B IMPLEMENTADA · 7C IMPLEMENTADA · 7D IMPLEMENTADA · 7E IMPLEMENTADA**

Rama: `v4-frontend-race`

Documento complementario a:

- `AUDITORIA_PRE_FASE7.md`
- `CANON_RECONSTRUCCION_FRONTEND_V4.md`
- `GAMEPLAY_V4.md`

## Alcance completado

### 7A — Capa de banco

Se creó:

`online/src/desafio_online/bank.py`

La capa V4 reutiliza sin modificar:

- `millonario_v3.model.Project`;
- `millonario_v3.model.Question`;
- `millonario_v3.storage.save_project()`;
- `millonario_v3.storage.load_project_with_recovery()`;
- `millonario_v3.excel_import.import_project_from_excel()`.

Responsabilidades implementadas:

1. banco único canónico;
2. validación adicional V4 de exactamente 12 preguntas;
3. rechazo de enunciados duplicados tras normalizar mayúsculas y espacios;
4. revisión SHA-256 de la representación normalizada;
5. `threading.RLock` para operaciones de lectura/publicación;
6. control optimista con `expected_revision`;
7. publicación atómica mediante el storage V3;
8. backups históricos `.bak`, `.bak2`, `.bak3`;
9. recovery histórico al cargar cuando la ruta es escribible;
10. modo de sólo lectura explícito;
11. si una ruta configurada está vacía, se siembra desde el banco del repositorio.

### Política de ruta

El wrapper V4 interpreta `QUESTION_BANK_PATH`.

```text
QUESTION_BANK_PATH configurado
→ usa esa ruta
→ escritura habilitada
→ si está vacía, siembra desde v3_1/projects/demo.juego

Desarrollo sin QUESTION_BANK_PATH
→ usa banco del repositorio
→ escritura habilitada para desarrollo

Producción sin QUESTION_BANK_PATH
→ usa banco del repositorio
→ sólo lectura
→ PUT/import devuelven error explícito
```

`configured_path` expresa que la ruta fue configurada por operación. No pretende detectar ni afirmar por sí sola que el volumen subyacente sea persistente.

## 7B — API transaccional

Se creó:

`online/src/desafio_online/questions_api.py`

Endpoints protegidos por la sesión de moderador existente:

```text
GET  /api/questions
PUT  /api/questions
GET  /api/questions/template
POST /api/questions/import
```

### GET /api/questions

Devuelve:

- título;
- 12 preguntas;
- cantidad;
- revisión SHA-256;
- `writable`;
- `storage_mode`.

### PUT /api/questions

Publica el banco completo en una única transacción.

Contrato:

- exactamente 12 preguntas;
- pregunta máximo 320 caracteres;
- cuatro alternativas;
- alternativa máximo 140 caracteres validado nuevamente por dominio V3;
- correcta 0–3;
- `expected_revision` obligatorio;
- conflicto de revisión → HTTP 409;
- banco inválido → HTTP 422;
- almacenamiento sólo lectura/no disponible → HTTP 503.

No se crearon endpoints separados para nueva/duplicar/borrar/mover. Esas operaciones pertenecerán al draft del navegador de 7C y se publicarán juntas mediante PUT.

### GET /api/questions/template

Sirve directamente el asset histórico:

`v3_1/templates/Banco_preguntas_V2.xlsx`

La web utilizará el texto **Descargar plantilla Excel**.

### POST /api/questions/import

Transporte deliberado: cuerpo binario `.xlsx`, sin multipart.

Metadata por query:

- `expected_revision`;
- `filename`.

Defensas de borde implementadas antes del parser histórico:

- máximo HTTP 2 MB;
- extensión `.xlsx`;
- ZIP válido;
- máximo 256 entradas internas;
- rechazo de ZIP cifrado;
- máximo 8 MB por entrada declarada;
- máximo 12 MB descomprimidos declarados;
- archivo temporal generado por servidor;
- ninguna extracción general del ZIP;
- borrado garantizado del temporal.

Después se ejecuta el importador V3 y la validación V4 de 12 preguntas antes de publicar.

No se agregó `openpyxl`, `python-multipart` ni otra dependencia.

## Integración con la aplicación

Para no realizar un reemplazo manual riesgoso de un `app.py` grande, el núcleo previo quedó preservado byte por byte como:

`online/src/desafio_online/app_core.py`

Su blob Git es el mismo que tenía `app.py` inmediatamente antes de Fase 7B:

`df6e212f9d3bfac0e3d8b9d7e47eb0f4810e3637`

El nuevo `app.py` es un wrapper pequeño que:

1. importa el núcleo anterior;
2. resuelve `QUESTION_BANK_PATH`;
3. construye `QuestionBankService`;
4. sustituye el `registry` del núcleo antes de atender solicitudes;
5. hace que toda sala nueva cargue la misma ruta de banco administrada;
6. monta el router `/api/questions`.

La máquina de juego, timers, WebSockets, auth, QR, clasificación, rondas y comodines permanecen en el núcleo sin modificaciones.

## Semántica de salas

Se conserva la regla fijada en la auditoría:

```text
Sala ya creada
→ mantiene su Project en memoria

Publicación de banco
→ cambia el banco maestro en storage
→ no muta salas existentes

Sala nueva
→ RoomRegistry carga el banco maestro actualizado
```

Replay de una sala existente continúa usando `room.project`; no salta al banco recién publicado.

## Pruebas añadidas

`online/tests/test_phase7_bank.py`

Cubre:

- siembra de ruta configurada;
- revisión;
- publicación + backup;
- conflicto de revisión;
- modo sólo lectura;
- requisito de 12 preguntas;
- duplicados normalizados.

`online/tests/test_phase7_api.py`

Cubre:

- autenticación real de moderador para GET;
- publicación manual y nueva revisión;
- stale write → 409;
- requisito de 12;
- sólo lectura → 503;
- descarga byte a byte de plantilla oficial;
- importación de la plantilla oficial;
- rechazo de archivo corrupto;
- rechazo de upload >2 MB.

### 7C — Administrador manual web

Se habilitó el botón **Administrador manual** en `online/static/admin.html`.

La interfaz incorporada mantiene el flujo V2/V3:

- lista izquierda de preguntas con contador `12 / 12`;
- selección inmediata;
- formulario derecho para enunciado, alternativas A/B/C/D y correcta A-D;
- límites visibles `320` y `140`;
- `+ Nueva`, `Duplicar`, `↑`, `↓` y `Eliminar` con confirmación;
- `Cancelar`, `Guardar banco` y `Cerrar`;
- indicador `Cambios sin guardar`;
- aviso claro de almacenamiento sólo lectura según `writable` del servidor.

Se agregó:

- `online/static/phase7_editor_logic.js`: operaciones puras de draft, validación, dirty state y serialización PUT;
- `online/static/phase7_editor.css`: presentación V3/Millonario aislada del resto de escenas;
- `online/tests/test_frontend_phase7_editor.py`: contratos de frontend y lógica JS.

El navegador trabaja siempre sobre un draft local. `Guardar banco` sólo se habilita si:

- el banco tiene exactamente 12 preguntas;
- las preguntas son válidas;
- hay cambios sin guardar;
- el servidor reporta `writable: true`.

La publicación usa exclusivamente:

```text
PUT /api/questions
```

con el banco completo y `expected_revision` tomado del `GET /api/questions` inicial. No se introdujo una API CRUD alternativa.

Errores:

- HTTP 409: informa cambio en otra pestaña y conserva el draft abierto;
- HTTP 422: muestra validación del servidor;
- HTTP 503/read-only: informa falta de almacenamiento persistente y conserva el draft.

Pruebas ejecutadas para el cierre de 7C:

```text
python -m pytest online/tests/test_frontend_phase1.py online/tests/test_frontend_phase6.py online/tests/test_frontend_phase7_editor.py online/tests/test_phase7_api.py online/tests/test_phase7_bank.py
```

Resultado: `34 passed, 1 warning`.

### 7D — Importación Excel web

Se habilitó el botón **Importar banco desde Excel** en `online/static/admin.html`.

La interfaz implementa el contrato web:

- **Descargar plantilla Excel** enlaza a `GET /api/questions/template`;
- selección de archivo `.xlsx` mediante input nativo;
- nombre de archivo visible;
- texto canónico: “La versión web requiere 12 preguntas activas para conservar los modos 1 / 3 / 5.”;
- confirmación explícita antes de reemplazar el banco actual;
- `Cancelar` y `Cargar banco`;
- estado read-only informado desde `GET /api/questions`.

Flujo técnico:

1. al abrir el importador se ejecuta `GET /api/questions`;
2. se conserva `revision` local;
3. el archivo se envía como cuerpo binario;
4. la URL incluye `expected_revision` y `filename`;
5. si el import falla, no se actualiza el estado local ni el banco;
6. si el import es exitoso, se guarda la nueva revisión devuelta por el servidor.

Endpoint usado:

```text
POST /api/questions/import?expected_revision=...&filename=...
```

Se mantiene el transporte binario sin `python-multipart`.

Errores:

- extensión distinta de `.xlsx`: rechazo inmediato;
- ZIP corrupto: HTTP 422 desde API;
- más de 2 MB: HTTP 413 desde API;
- 4–11 preguntas activas válidas: HTTP 422 con explicación V4 de 12 preguntas;
- stale revision: HTTP 409;
- read-only: HTTP 503 explícito;
- import fallido: revisión/banco sin cambios.

Pruebas ejecutadas para el cierre de 7D:

```text
python -m pytest online/tests/test_frontend_phase1.py online/tests/test_frontend_phase6.py online/tests/test_frontend_phase7_editor.py online/tests/test_phase7_api.py online/tests/test_phase7_bank.py
```

Resultado: `40 passed, 1 warning`.

### 7E — Persistencia y QA del banco

Se validó la arquitectura definida sin modificar infraestructura de Render.

Contratos cubiertos:

- `QUESTION_BANK_PATH` vacío/configurado se inicializa desde el banco semilla;
- publicación crea `.bak`;
- recovery restaura el primario desde backup válido;
- dos pestañas no pueden sobrescribir por `expected_revision`;
- una sala creada antes de editar conserva su `Project`;
- una sala nueva usa el banco publicado;
- replay de sala existente conserva `room.project`;
- UX no reintroduce “Mis bancos” ni usa `/api/banks`;
- modo read-only sigue devolviendo error explícito.

Pruebas nuevas:

- `online/tests/test_phase7_persistence.py`.

También se ajustaron dos contratos estáticos antiguos:

- Fase 2 acepta que `host.js` oculte métricas con `classList.add("hidden")`, coherente con Fase 3 y con el canon anti-dashboard;
- la prueba de autenticación de `/api/questions` limpia el rate limiter antes de login para no depender del orden de ejecución de toda la suite.

Pruebas ejecutadas para el cierre de 7E:

```text
python -m pytest online/tests
```

Resultado: `86 passed, 1 warning`.

## Estado de infraestructura

No se modificó Render.

La producción actual no tiene `QUESTION_BANK_PATH` persistente configurado, por lo que cuando esta rama se pruebe con `ENVIRONMENT=production` el editor podrá leer el banco pero las publicaciones serán rechazadas de forma explícita hasta configurar persistencia real.

No se creó PostgreSQL.

## Siguiente bloque

### Fase 8 — Comodines y público extremo a extremo

Auditar y fortalecer, sin reconstruir si ya funciona:

- 50:50 host/móvil/backend;
- llamada 15 s con timer pausado y música sin pausa;
- público 15 s, jugadores excluidos, agregación A-D y retorno limpio a pregunta.
