# Avance — Reconstrucción Frontend V4

Documento operativo complementario a `CANON_RECONSTRUCCION_FRONTEND_V4.md`.

> **Orden operativo vigente:** Fase 3 consolidó todas las escenas visuales; Fase 4 audio canónico host; Fase 5 móvil silencioso; Fase 6 selector 1/3/5; Fase 7 editor/Excel. Esta bitácora prevalece para saber dónde continuar.

## Estado general

- Rama: `v4-frontend-race`
- Base protegida: `main`
- Producción/Render: sin cambios durante la reconstrucción
- `v3_1/`: protegido como referencia canónica; no modificar para resolver necesidades V4
- Fuente visual: V2/V3/PPT
- Audio: `docs/AUDIO_CUES_V4.md`
- Gameplay: `docs/GAMEPLAY_V4.md`
- Móvil: `docs/MOBILE_PULSADOR_V4.md`
- Fase 7: `docs/AUDITORIA_PRE_FASE7.md` + `docs/FASE7_EDITOR_BANCO.md`

## Estado por fase

| Fase | Estado | Alcance |
|---|---|---|
| 0 | COMPLETADA | Canon y rama |
| 1 | IMPLEMENTADA / pendiente validación visual | Home, Moderador, login, menú |
| 2 | IMPLEMENTADA VISUAL / pendiente validación visual | Lobby V3 sobre V4 |
| 3 | IMPLEMENTADA VISUAL / pendiente navegador | Clasificatoria, resultados, clasificados, rondas, preguntas y cierres |
| 4 | IMPLEMENTADA HOST / pendiente escucha | Audio canónico PPT/V3 |
| 5 | IMPLEMENTADA / pendiente móvil real | Pulsador 100 % silencioso |
| 6 | IMPLEMENTADA / pendiente runtime | Selector autoritativo 1/3/5 |
| 7A | IMPLEMENTADA / pendiente runtime | Capa de banco V4, revisión, backups, read-only |
| 7B | IMPLEMENTADA / pendiente runtime | API GET/PUT/template/import |
| 7C | IMPLEMENTADA / pendiente navegador | Administrador manual web |
| 7D | IMPLEMENTADA / pendiente navegador | Interfaz importación Excel |
| 7E | IMPLEMENTADA / sin cambios Render | Persistencia y QA del banco |
| 8 | VALIDADA / pendiente navegador real | Comodines/público extremo a extremo |
| 9 | VALIDADA / pendiente navegador real | Replay/continuidad |
| 10 | VALIDADA / pendiente dispositivos reales | Pulido visual/responsive |
| 11 | QA AUTOMATIZADA PARCIAL / bloqueos manuales | QA, merge y producción |

## Contratos acumulados que no deben reinterpretarse

1. `main` y Render no se modifican hasta validación final.
2. Home usa `Moderador`; no hay entrada manual de código ni `Mis bancos`.
3. Lobby: QR/código/conectados 30/selector 1-3-5/participantes.
4. Clasificatoria: todos, 30 s, ranking correcto + velocidad servidor, dos clasificados.
5. No clasificados permanecen como público.
6. Dos rondas, N = 1/3/5 preguntas por jugador, 45 s cada una.
7. 50:50 automático; llamada y público 15 s; público agrega A-D y gráfica.
8. Host contiene toda la dramaturgia audiovisual; móviles audio = 0.
9. Replay conserva sala/tokens/identidades y vuelve a clasificatoria sin QR.
10. Banco publicado V4 = exactamente 12 preguntas.

## Fases 1–6 — resumen de implementación

- Fase 1: menú V3 recuperado sobre autenticación V4.
- Fase 2: lobby reconstruido; selector colocado en posición definitiva.
- Fase 3: escenas V3/PPT para clasificatoria, resultados, clasificados, rondas, pregunta, revelación y final.
- Fase 4: `sound.js` separado en music/cue/effect/voice y `phase4_audio.js` con idempotencia; `transition.mp3` precede `question_music.mp3`; llamada/público se superponen a la tensión.
- Fase 5: `play.html`/`play.js` sin audio; pulsador conserva token, WS, heartbeat, reconexión, roles, timer y A-D.
- Fase 6: `OnlineSessionOrchestrator` limita los bloques V3 de 5 a N=1/3/5 sin modificar el plan maestro 12 ni `v3_1/`.

## Fase 7 — estado actual

### Auditoría cerrada

`docs/AUDITORIA_PRE_FASE7.md` fijó:

- reutilizar `Question`, `Project`, `excel_import` y `storage` V3;
- un único banco canónico;
- exactamente 12 preguntas publicadas;
- no introducir PostgreSQL para este MVP;
- almacenamiento configurable por `QUESTION_BANK_PATH`;
- producción sin persistencia configurada debe ser sólo lectura, nunca falso guardado;
- salas existentes conservan su `Project`; banco nuevo afecta sólo a salas nuevas.

### 7A implementada

Nuevo `online/src/desafio_online/bank.py`:

- revisión SHA-256;
- `RLock`;
- `expected_revision` para concurrencia optimista;
- publicación atómica reutilizando `save_project()` V3;
- backups `.bak/.bak2/.bak3`;
- recovery histórico;
- validación exacta de 12;
- duplicados normalizados rechazados;
- siembra de ruta configurada vacía desde el banco del repositorio;
- modo sólo lectura explícito.

Pruebas: `online/tests/test_phase7_bank.py`.

### 7B implementada

Nuevo `online/src/desafio_online/questions_api.py`:

```text
GET  /api/questions
PUT  /api/questions
GET  /api/questions/template
POST /api/questions/import
```

Todo requiere sesión del moderador.

Import Excel:

- cuerpo binario, sin multipart;
- máximo 2 MB;
- ZIP válido;
- límites de entradas/tamaño descomprimido;
- no extracción general;
- temporal generado por servidor y eliminado siempre;
- parser V3 + validación V4 exacta de 12.

No se añadieron dependencias.

Para minimizar riesgo, el `app.py` previo se conservó byte por byte como `app_core.py` (blob previo `df6e212f9d3bfac0e3d8b9d7e47eb0f4810e3637`). El nuevo `app.py` es un wrapper pequeño que configura el banco, sustituye el registry antes de servir tráfico y monta el router nuevo. Las rutas históricas permanecen en `app_core.py` sin reescritura.

Pruebas: `online/tests/test_phase7_api.py`.

### 7C implementada

Administrador manual habilitado en `/admin`:

- `GET /api/questions` carga banco, `revision`, `writable` y `storage_mode`;
- draft local completo con lista izquierda y formulario derecho;
- Nueva, Duplicar, mover arriba, mover abajo y Eliminar con confirmación;
- límites/counters `320` para enunciado y `140` por alternativa;
- correcta A-D;
- indicador `Cambios sin guardar`;
- cierre/cancelación con confirmación de descarte;
- `Guardar banco` usa `PUT /api/questions` con `expected_revision`;
- HTTP 409, 422 y 503/read-only se informan sin destruir el draft;
- guardar sólo se habilita con exactamente 12 preguntas válidas y servidor escribible.

Archivos nuevos:

- `online/static/phase7_editor_logic.js`;
- `online/static/phase7_editor.css`;
- `online/tests/test_frontend_phase7_editor.py`.

También se ajustó `online/static/phase6_settings.js` para conservar la forma esperada por el contrato estático de Fase 6 sin cambiar la semántica del selector.

Pruebas ejecutadas:

```text
python -m pytest online/tests/test_frontend_phase1.py online/tests/test_frontend_phase6.py online/tests/test_frontend_phase7_editor.py online/tests/test_phase7_api.py online/tests/test_phase7_bank.py
```

Resultado: `34 passed, 1 warning`.

### 7D implementada

Importación Excel habilitada en `/admin`:

- `GET /api/questions` carga revisión y estado `writable`;
- `Descargar plantilla Excel` apunta a `GET /api/questions/template`;
- selector `.xlsx` con nombre de archivo visible;
- aviso de que V4 requiere 12 preguntas activas para conservar 1/3/5;
- confirmación antes de reemplazar el banco;
- `POST /api/questions/import` usa cuerpo binario y query `filename` + `expected_revision`;
- import exitoso actualiza la revisión local;
- import fallido no modifica banco ni estado local;
- 409, 422, 413 y 503/read-only se muestran de forma explícita.

Pruebas agregadas/fortalecidas:

- UI de importación y descarga de plantilla;
- upload binario con `filename` y `expected_revision`;
- archivo no `.xlsx`;
- ZIP corrupto;
- upload `>2 MB`;
- 4–11 preguntas válidas rechazadas por política V4;
- stale revision → 409;
- read-only → 503 explícito;
- import fallido conserva revisión;
- import exitoso cambia revisión.

Pruebas ejecutadas:

```text
python -m pytest online/tests/test_frontend_phase1.py online/tests/test_frontend_phase6.py online/tests/test_frontend_phase7_editor.py online/tests/test_phase7_api.py online/tests/test_phase7_bank.py
```

Resultado: `40 passed, 1 warning`.

### 7E implementada

Persistencia y QA del banco validadas sin configurar infraestructura:

- ruta configurada vacía se inicializa desde banco semilla;
- publicaciones generan backup;
- recovery restaura desde backup válido;
- `expected_revision` evita sobrescritura entre pestañas;
- sala existente conserva su `Project` tras editar banco maestro;
- sala nueva toma el banco publicado;
- replay conserva `room.project`;
- UX no reintroduce multi-bank ni “Mis bancos”;
- producción/read-only mantiene error explícito.

Pruebas nuevas:

- `online/tests/test_phase7_persistence.py`.

Pruebas ejecutadas:

```text
python -m pytest online/tests
```

Resultado: `86 passed, 1 warning`.

## Fase 8 — estado actual

### Comodines y público validados

Se auditó la implementación existente sin reconstruir lógica funcional.

Contratos cubiertos:

- 50:50 elimina exactamente dos incorrectas;
- la correcta permanece;
- `allowed_answers` móvil refleja las alternativas disponibles;
- el servidor rechaza respuestas a letras eliminadas;
- el mismo comodín no se repite en una pregunta;
- llamada abre ventana de 15 s;
- llamada pausa el timer de pregunta en servidor y reanuda con tiempo restante;
- público abre ventana de 15 s;
- jugadores seleccionados quedan excluidos;
- sólo público vota;
- agregación A/B/C/D devuelve cantidad, porcentaje y total;
- cierre de comodín vuelve a `question_active`;
- audio host mantiene idempotencia por `last_event.id`;
- llamada/público no detienen `question_music` ni repiten `transition.mp3`;
- móvil sigue keys-only y silencioso.

Pruebas nuevas:

- `online/tests/test_phase8_lifelines.py`.

Pruebas ejecutadas:

```text
python -m pytest online/tests/test_phase8_lifelines.py online/tests/test_game_flow.py online/tests/test_app.py online/tests/test_frontend_phase4.py online/tests/test_frontend_phase5.py
```

Resultado: `35 passed, 1 warning`.

## Fase 9 — estado actual

### Replay y continuidad validados

Se auditó `OnlineRoom.repeat()` y `RoomManager.reset_for_replay()` sin reconstruir el flujo.

Contratos cubiertos:

- `Repetir juego` conserva el mismo código de sala;
- tokens existentes siguen autenticando al mismo participante;
- device IDs, alias y avatar se mantienen;
- participantes registrados permanecen en la sala;
- roles vuelven a público;
- seleccionados/preseleccionados quedan vacíos;
- scores y usos de comodines vuelven a cero;
- respuestas, lifelines, clasificación, timers y pregunta activa se limpian;
- se genera nuevo plan de 12 preguntas;
- todos pueden entrar a una nueva clasificatoria sin QR nuevo;
- el modo 1/3/5 se conserva inicialmente y puede cambiarse en lobby;
- replay conserva `room.project` aunque el banco maestro cambie.

Pruebas nuevas:

- `online/tests/test_phase9_replay.py`.

Pruebas ejecutadas:

```text
python -m pytest online/tests/test_phase9_replay.py online/tests/test_frontend_phase6.py online/tests/test_game_flow.py
```

Resultado: `23 passed, 1 warning`.

## Fase 10 — estado actual

### Pulido visual validado en navegador local

Se revisaron vistas host, móvil y administración con Chromium local, sin agregar funcionalidades grandes ni tocar la política audiovisual.

Contratos cubiertos:

- lobby host en 1366×768 con 30 participantes visible sin corte inferior;
- lobby host en 1920×1080 conserva grilla y jerarquía V3;
- escena de pregunta en 1366×768 mantiene timer, respuestas 2×2 y controles sin scroll;
- escena de pregunta en 1920×1080 conserva composición 16:9;
- móvil en viewport Pixel 5 mantiene pulsador silencioso y CTA visible;
- administración manual conserva foco de edición, herramientas y botones finales dentro de viewport;
- importación Excel no muestra “Abrir carpeta de plantilla” y usa control visible `Seleccionar archivo`;
- no se modificó `v3_1/`, WebSockets, timers, replay, audio móvil ni infraestructura.

Ajustes realizados:

- compactación responsive del lobby host para alturas de laptop;
- compactación responsive de la escena de pregunta para evitar scroll en 1366×768;
- control de archivo Excel estilizado y legible;
- herramientas del editor manual redistribuidas para evitar botones estrechos.

Validación visual local:

```text
http://127.0.0.1:8000
Chromium / Playwright
1366×768, 1920×1080, Pixel 5
```

Pruebas ejecutadas:

```text
python -m pytest online/tests/test_frontend_phase2.py online/tests/test_frontend_phase3.py online/tests/test_frontend_phase5.py online/tests/test_frontend_phase7_editor.py
```

Resultado: `28 passed, 1 warning`.

Suite completa ejecutada:

```text
python -m pytest online/tests
```

Resultado: `94 passed, 1 warning`.

## Persistencia de producción

Render no fue modificado.

Mientras producción no tenga `QUESTION_BANK_PATH` apuntando a almacenamiento persistente:

```text
GET banco → permitido
PUT/import → rechazado explícitamente como sólo lectura
```

La infraestructura persistente queda pendiente de autorización explícita; no se configuró Persistent Disk.

## Fase 11 — estado actual

### QA pre-merge automatizada parcial

Se ejecutó la parte automatizable local sin merge, sin deploy y sin cambios de infraestructura.

Pruebas ejecutadas:

```text
python -m pytest online/tests
```

Resultado: `98 passed, 1 warning`.

Cobertura nueva agregada:

- `online/tests/test_phase11_premerge.py`;
- recorridos API completos para modos 1, 3 y 5;
- lobby → clasificatoria → selección → dos rondas → final → replay;
- replay conserva código y tokens y permite cambiar modo al volver a lobby;
- 30 participantes desde la misma IP;
- participante 31 rechazado por sala llena;
- 30 participantes pueden completar clasificatoria.

Pruebas V3 no-Qt ejecutadas:

```text
python -m pytest v3_1/tests/test_session.py v3_1/tests/test_room.py v3_1/tests/test_load.py v3_1/tests/test_live_service.py v3_1/tests/test_api.py
```

Resultado: `22 passed, 1 warning`.

Pruebas raíz no-Qt ejecutadas:

```text
$env:PYTHONPATH='src'; python -m pytest tests/test_engine.py tests/test_excel_rounds.py tests/test_model_storage.py
```

Resultado: `17 passed`.

Suite amplia intentada:

```text
python -m pytest v3_1/tests tests online/tests
```

Resultado: bloqueada en colección por entorno:

- `PySide6` no está instalado;
- el entorno actual usa Python `3.14.4`, mientras `pyproject.toml` declara `requires-python = ">=3.12,<3.14"`;
- tests raíz sin `PYTHONPATH=src` no resuelven `millonario`.

Revisión pre-merge local:

- `git diff --name-status main...HEAD` revisado;
- `git diff --name-status -- v3_1` sin cambios locales;
- búsqueda básica de secretos/config no encontró valores sensibles, sólo nombres de variables y documentación;
- Render no fue desplegado ni configurado.

Bloqueos restantes antes de considerar PR final:

- instalar entorno compatible con PySide6/Python soportado y ejecutar suite Qt;
- recorridos manuales reales 1/3/5 en navegador con moderador;
- escucha real de audio host;
- validación de teléfonos físicos Android/iOS y silencio absoluto;
- fullscreen Chrome desktop;
- revisión final de diff y preparación de PR sin merge.

## Validaciones globales pendientes antes de main

- ejecutar suite completa con PySide6 en Python soportado;
- validación visual completa Fases 1–3 en dispositivos finales;
- escucha host Fase 4;
- varios móviles silenciosos y reconexión Fase 5;
- partidas completas 1/3/5 Fase 6;
- editor/importador Fase 7;
- comodines/público;
- replay;
- Chrome desktop + iOS/Android + fullscreen;
- Render/WebSocket.

## Restricciones vigentes

- No tocar audio sin `AUDIO_CUES_V4.md`.
- No reintroducir audio móvil.
- No modificar 1/3/5 sin `GAMEPLAY_V4.md`.
- No tocar `v3_1/` para necesidades V4.
- No desplegar `v4-frontend-race` ni fusionar a `main` antes de validación final.

## Próximo checkpoint

**Fase 11 — QA completo, pre-merge.**

Debe ejecutar suite completa real, recorridos 1/3/5, 30 participantes, comodines, escucha de audio en navegador, móviles reales disponibles y revisión de diff antes de preparar PR. Detenerse antes de merge y deploy.
