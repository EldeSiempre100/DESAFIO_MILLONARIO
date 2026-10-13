# Contrato de gameplay V4 — Desafío Millonario

Estado: **VIGENTE — Fase 6 implementada**

Rama: `v4-frontend-race`

Este documento fija la dinámica autoritativa de V4. Complementa:

- `CANON_RECONSTRUCCION_FRONTEND_V4.md` — dirección general;
- `AUDIO_CUES_V4.md` — dramaturgia audiovisual del host;
- `MOBILE_PULSADOR_V4.md` — contrato del teléfono.

## 1. Principio

V4 conserva la dinámica participativa de V3.1.4 y añade una única parametrización de duración de ronda:

> El moderador elige **1, 3 o 5 preguntas por jugador** antes de iniciar la clasificatoria.

La selección no cambia clasificatoria, número de jugadores, timers, comodines, roles, WebSockets ni repetición.

## 2. Banco y plan maestro

El banco canónico sigue conteniendo exactamente **12 preguntas activas**.

El `QuestionPlan` V3 se conserva intacto:

```text
1 clasificatoria
+ 5 preguntas potenciales de ronda 1
+ 5 preguntas potenciales de ronda 2
+ 1 reserva
= 12 preguntas únicas
```

V4 **no modifica `v3_1/`** para implementar modos cortos.

`OnlineSessionOrchestrator` hereda el orquestador V3 y consume solamente las primeras N preguntas de cada bloque de ronda:

```text
N = 1, 3 o 5

clasificatoria
+ primeras N del bloque V3 de ronda 1
+ primeras N del bloque V3 de ronda 2
+ reserva conservada en el plan
```

Las preguntas no consumidas en modos 1 y 3 permanecen en el plan maestro pero no se abren en esa partida.

## 3. Momento de configuración

Estado permitido para modificar `questions_per_round`:

```text
LOBBY_OPEN
```

Valores válidos:

```text
1 | 3 | 5
```

Una vez iniciada la clasificatoria, la configuración queda bloqueada por servidor. No depende de que el botón del navegador esté deshabilitado.

El endpoint autoritativo es:

```text
POST /api/games/{room_code}/settings
{"questions_per_round": 1|3|5}
```

El snapshot del host devuelve:

```text
settings.questions_per_round
```

para reconciliar interfaz, recargas y reconexiones del moderador.

## 4. Clasificatoria

No cambia con el modo de ronda.

- participan todos los enrolados elegibles;
- duración: 30 s;
- respuestas A/B/C/D;
- servidor ordena respuestas correctas por tiempo recibido;
- los dos mejores aciertos quedan preseleccionados;
- si faltan aciertos, se completan cupos de forma segura con participantes disponibles;
- el moderador confirma exactamente dos jugadores.

## 5. Rondas

Se juegan siempre dos rondas, una por cada clasificado.

```text
Ronda 1 → jugador 1 → N preguntas
Ronda 2 → jugador 2 → N preguntas
```

Cada pregunta regular mantiene:

- 45 s;
- respuesta única del jugador activo;
- servidor como autoridad del timer y respuesta;
- score de una unidad por acierto;
- avance a `ROUND_SUMMARY` exactamente al terminar la pregunta N.

El payload `round.question_total` y `question.question_total` debe ser siempre N; no se permite un hardcode visual o API a 5.

## 6. Comodines

Reglas V3 conservadas:

- `50:50`;
- `Llamada`;
- `Consulta al público`;
- máximo nominal de 3 usos de cada tipo por ronda;
- el mismo comodín no puede utilizarse más de una vez en una misma pregunta;
- llamada y público abren 15 s y pausan el timer de pregunta;
- 50:50 es automático y no pausa el timer.

Consecuencia natural del modo corto:

- con 1 pregunta, cada tipo de comodín sólo puede usarse efectivamente una vez en la ronda por la regla de una vez por pregunta;
- con 3 preguntas, puede alcanzar los 3 usos nominales;
- con 5 preguntas, conserva el comportamiento completo V3.

La interfaz debe evitar prometer tres usos efectivos en el modo de 1 pregunta.

## 7. Público

Los participantes no clasificados permanecen conectados.

Durante `Consulta al público`:

- sólo participantes con rol público son elegibles;
- reciben A/B/C/D durante 15 s;
- los dos jugadores seleccionados quedan excluidos;
- servidor agrega votos;
- host muestra gráfica A/B/C/D;
- al terminar, la pregunta del jugador continúa con el tiempo restante.

## 8. Móvil

No cambia por el selector.

El pulsador sigue mostrando solamente:

- identidad/rol/conexión;
- A/B/C/D cuando el servidor habilita una apertura;
- timer visual;
- feedback de respuesta.

No recibe enunciado ni textos de alternativas y permanece 100 % silencioso.

## 9. Audio

No cambia por el selector.

Cada pregunta regular que realmente se abre genera su cue canónico:

```text
transition.mp3
→ question_music.mp3
```

Por tanto:

- modo 1: un cue/pregunta por ronda;
- modo 3: tres cues/preguntas por ronda;
- modo 5: cinco cues/preguntas por ronda.

Los demás estados siguen `AUDIO_CUES_V4.md`.

## 10. Repetición

`Repetir juego` conserva sala, teléfonos, tokens e identidades.

La selección 1/3/5 también se conserva inicialmente al recrear el plan. Como el replay vuelve a `LOBBY_OPEN`, el moderador puede cambiarla antes de iniciar la nueva clasificatoria.

## 11. Implementación

Archivos principales de Fase 6:

- `online/src/desafio_online/session.py` — adaptador web de `SessionOrchestrator`;
- `online/src/desafio_online/registry.py` — setting persistido y payloads dinámicos;
- `online/src/desafio_online/app.py` — API `Literal[1,3,5]`;
- `online/static/phase6_settings.js` — selector/reconciliación del lobby;
- `online/static/host.html` — botones 1/3/5 habilitados;
- `online/tests/test_frontend_phase6.py` — pruebas integrales 1/3/5.

## 12. Invariantes protegidos

Fase 6 no debe cambiar:

- las 12 preguntas del banco maestro;
- el archivo `v3_1/src/millonario_v3/session.py`;
- clasificatoria de 30 s;
- dos jugadores;
- pregunta regular de 45 s;
- comodines y límites V3;
- público conectado;
- WebSockets/reconexión;
- audio del host;
- silencio del móvil.

## 13. Criterios de aceptación

Antes de fusionar a `main` deben comprobarse los tres recorridos completos:

### Modo 1

- ronda 1 termina después de 1 pregunta;
- ronda 2 termina después de 1 pregunta;
- score máximo por jugador: 1;
- intro y contador muestran 1;
- no aparece una segunda pregunta.

### Modo 3

- cada ronda abre exactamente 3 preguntas;
- `question_number` avanza 1→2→3;
- al revelar la tercera pasa a resumen;
- score máximo por jugador: 3.

### Modo 5

- comportamiento equivalente al canon V3;
- cinco preguntas por jugador;
- score máximo: 5.

### Para los tres

- plan maestro conserva 12 IDs únicos;
- selector no puede modificarse después de iniciar clasificatoria;
- 45/30/15 s se mantienen;
- móviles y público reciben aperturas correctas;
- replay conserva el modo y permite cambiarlo nuevamente en lobby.
