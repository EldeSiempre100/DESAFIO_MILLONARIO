# Contrato audiovisual V4 — Desafío Millonario

Estado: **VIGENTE — Fase 4**

Rama: `v4-frontend-race`

Este documento complementa `CANON_RECONSTRUCCION_FRONTEND_V4.md` y fija la política de reproducción del **host/moderador**. No redefine lógica de juego, timers ni estados del servidor.

## 1. Fuentes y criterio de reconstrucción

Jerarquía aplicada:

1. `Quien quiere ser millonario FEB 2026.pptx`: fuente maestra declarada de lenguaje audiovisual y ritmo del producto.
2. Material PPT histórico del mismo linaje que conserva internamente secuencias multimedia y timing (`JUEGO millonario inchim.pptx`): evidencia recuperable de la coreografía de entrada de pregunta.
3. V3.1.4 (`v3_1/src/millonario_v3/audio.py` y `participative_controller.py`): fuente de cómo ese lenguaje fue adaptado al modo participativo.
4. Assets runtime de V3.1.4 (`v3_1/assets/audio/`): archivos que deben reproducirse en V4.
5. V4 anterior a esta fase: no es fuente maestra cuando contradice los puntos anteriores.

La copia Office histórica conserva en su XML de pregunta una primera reproducción multimedia de **11 493 ms (≈ 11,493 s)** y un segundo medio que comienza después de `delay="11493"`. Esa relación corresponde al patrón **cue de entrada → música sostenida de pregunta**. En V3 los assets equivalentes sobreviven como `transition.mp3` y `question_music.mp3`.

La reconstrucción web no utiliza el video/temporizador del PowerPoint como reloj. V4 mantiene su timer autoritativo de servidor y usa el material PPT únicamente para la dramaturgia audiovisual.

## 2. Assets runtime

Los archivos canónicos ya existentes son:

| Rol | Asset V3/V4 |
|---|---|
| Ambiente / apertura | `intro.mp3` |
| Entrada de pregunta | `transition.mp3` |
| Tensión sostenida | `question_music.mp3` |
| Respuesta correcta | `correct.wav` |
| Respuesta incorrecta / timeout | `incorrect.wav` |
| 50:50 / activación de comodín | `lifeline.wav` |
| Llamada | `call.mp3` |
| Consulta al público | `audience.wav` |

No se crean pistas nuevas en Fase 4.

## 3. Regla central

La pantalla del moderador es el escenario audiovisual.

La experiencia participativa V3 añadió la clasificatoria sin convertirla en una segunda ronda de pregunta tradicional. Por eso el ambiente `intro.mp3` se mantiene durante:

```text
LOBBY
→ CLASIFICATORIA
→ RESULTADO CLASIFICATORIO
→ DOS CLASIFICADOS
→ INTRO DE RONDA
```

Este punto está respaldado por `ParticipativeController.startParticipation()`, que inicia `intro`, mientras `openQualifier()` no cambia a música de pregunta. La música `question_music.mp3` se inicia en V3 al abrir una **pregunta regular de ronda**.

## 4. Máquina de cues del host

### Administración

```text
HOME / LOGIN / EDITOR
→ silencio
```

No se debe activar audio automáticamente antes de entrar a la experiencia.

### Lobby y clasificatoria

```text
CREAR / ABRIR SALA
→ interacción explícita del moderador desbloquea audio del navegador
→ intro.mp3 en loop

CLASIFICATORIA 30 s
→ continúa intro.mp3

RESULTADO CLASIFICATORIO
→ continúa intro.mp3

JUGADORES CLASIFICADOS
→ continúa intro.mp3

INTRO DE RONDA
→ continúa intro.mp3
```

No reproducir `transition.mp3` entre esos estados.

### Pregunta regular

Al recibirse el evento autoritativo `question_started`:

```text
cancelar cualquier secuencia anterior
→ detener ambiente anterior
→ transition.mp3
→ al terminar el cue (≈ 11,49 s; fallback técnico 11,65 s)
→ question_music.mp3 en loop
```

La transición se reproduce **una sola vez por `question_started`**. El polling de snapshots no puede volver a dispararla.

Si el host recarga la página a mitad de una pregunta, se retoma directamente `question_music.mp3`; no se simula una entrada que ya ocurrió.

### Respuesta

Al recibirse `answer_revealed`:

```text
cancelar cue pendiente, si existe
→ detener/fadear música de tensión
→ detener voz de comodín, si existe
→ correct.wav O incorrect.wav
```

Un timeout utiliza el tratamiento de respuesta incorrecta.

### Siguiente pregunta

La siguiente pregunta genera un nuevo `question_started`, por lo que vuelve a ejecutar:

```text
transition.mp3
→ question_music.mp3
```

### 50:50

```text
question_music continúa
+
lifeline.wav superpuesto
```

El 50:50 no reemplaza la cama musical porque no pausa la pregunta.

### Llamada

El backend pausa el timer de pregunta y abre una ventana de 15 s. **La pausa del reloj no implica detener la cama musical.** En V3 `question_music` y `call.mp3` se reproducen en canales distintos y el controlador no ejecuta `stop_music()` al activar llamada.

```text
question_music continúa
+
lifeline.wav
+ call.mp3
→ al terminar el comodín:
   detener call.mp3
   continuar la misma question_music
```

No repetir `transition.mp3` al cerrar llamada: sigue siendo la misma pregunta.

### Consulta al público

Misma arquitectura que llamada. V3 usa un canal de voz independiente para `audience.wav`, sin detener la cama musical.

```text
question_music continúa
+
lifeline.wav
+ audience.wav
→ gráfica de público
→ al terminar el comodín:
   detener audience.wav
   continuar la misma question_music
```

No repetir `transition.mp3`.

Si un comodín se activa excepcionalmente durante el cue de entrada, el cue no se cancela: la pista de voz se superpone y la secuencia de entrada continúa hasta `question_music`, manteniendo la separación de canales del diseño V3.

### Fin de ronda / nueva ronda / final

```text
ROUND_SUMMARY
→ intro.mp3

ROUND_INTRO siguiente
→ continúa intro.mp3

SESSION_SUMMARY
→ intro.mp3
```

En web, `intro.mp3` se mantiene en loop mientras estas pantallas permanezcan visibles. Es una adaptación práctica de una pantalla de duración indeterminada, no un cambio de lógica de juego.

## 5. Idempotencia y polling

El host consulta estado periódicamente. El audio debe obedecer eventos, no el mero hecho de volver a recibir el mismo snapshot.

Reglas:

- persistir el último `last_event.id` procesado en `sessionStorage`;
- un evento se procesa sólo si su ID es mayor al último procesado;
- reconciliar estado después para recargas/reconexión, sin volver a ejecutar cues dramáticos;
- `question_started` tiene protección adicional mediante token de secuencia;
- sólo puede existir una secuencia `transition → question_music` vigente;
- llamada/público usan el canal `voice` y no destruyen la secuencia/música de pregunta;
- responder durante la entrada sí cancela el cue antes de reproducir correcto/incorrecto.

## 6. Canales de reproducción

`GameAudio` utiliza canales independientes:

- `music`: ambiente o tensión en loop;
- `cue`: entrada de pregunta, no loop;
- `effect`: correcto, incorrecto y efecto de comodín;
- `voice`: llamada o público.

La separación de canales es funcional: permite que llamada/público se superpongan a la tensión exactamente como permite la arquitectura de audio V3, sin mezclar responsabilidades ni reiniciar pistas por polling.

## 7. Autoplay y control del moderador

Los navegadores requieren una interacción del usuario para desbloquear audio. V4 mantiene un botón visible `Activar sonido / Silenciar`.

Una vez desbloqueado:

- se precargan los assets críticos;
- el servidor sigue siendo quien decide los cambios de estado;
- el navegador sólo decide qué pista corresponde al evento recibido.

Si el usuario habilita audio a mitad de una pregunta, comienza directamente la tensión vigente en vez de representar cues históricos ya ocurridos.

## 8. Teléfonos

**Fase 4 sólo corrige la política del host.**

Los móviles todavía contienen la implementación audiovisual anterior y serán corregidos en **Fase 5 — Pulsador móvil silencioso**. Hasta completar Fase 5 no debe declararse cumplido el criterio global “audio exclusivamente en host”.

La meta ya fijada sigue siendo:

> Pulsadores móviles 100 % silenciosos.

## 9. Implementación Fase 4

Archivos:

- `online/static/sound.js`: canales, secuenciador, cancelación y precarga.
- `online/static/phase4_audio.js`: política de cues del host y reconciliación por eventos/estado.
- `online/static/host.html`: carga explícita de la política después de `host.js`.
- `online/tests/test_frontend_phase4.py`: contratos estáticos de esta fase.

`phase4_audio.js` se carga después de `host.js` y sustituye únicamente los bindings globales `backgroundForState`, `renderLifelines` y `syncAudio`. Esta separación mantiene aislada la política audiovisual sin modificar backend ni reescribir nuevamente las escenas de Fase 3.

## 10. Criterios de aceptación auditiva

Antes de fusionar a `main` se debe escuchar una partida completa y confirmar:

1. lobby, clasificatoria, resultado y selección mantienen continuidad de ambiente;
2. cada pregunta regular tiene una sola entrada antes de tensión;
3. responder durante la entrada cancela correctamente el cue;
4. correcto/incorrecto no compiten con música de tensión;
5. 50:50 no corta la tensión;
6. llamada y público se superponen a la tensión mientras el timer permanece pausado;
7. ningún snapshot repetido vuelve a disparar un cue;
8. recargar el host no reinicia una entrada histórica;
9. silenciar detiene todos los canales;
10. Fase 5 elimina completamente el audio de teléfonos.
