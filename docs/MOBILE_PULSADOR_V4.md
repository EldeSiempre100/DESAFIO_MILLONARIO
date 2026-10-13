# Contrato móvil V4 — Pulsador interactivo

Estado: **VIGENTE — Fase 5 implementada**

Rama: `v4-frontend-race`

Este documento fija el comportamiento del cliente participante y **prevalece sobre cualquier nota histórica anterior** que indique que el audio móvil está pendiente de retirar. En particular, actualiza el estado descrito durante Fase 4 en `AUDIO_CUES_V4.md`.

## 1. Propósito

El teléfono no es una segunda pantalla audiovisual del concurso.

Su función es ser un **pulsador interactivo silencioso**, robusto y de baja carga cognitiva, siguiendo la filosofía de V3.1.4 y utilizando la conectividad multi-red/WebSocket de V4.

## 2. Regla audiovisual

**Audio del cliente participante: 0.**

`/join/{room_code}` no debe:

- cargar `sound.js`;
- crear `GameAudio`;
- crear objetos `Audio`;
- reproducir `intro.mp3`;
- reproducir `question_music.mp3`;
- reproducir `transition.mp3`;
- reproducir correcto/incorrecto;
- reproducir efectos de comodines;
- reproducir sonidos al enrolarse;
- ofrecer botón `Activar sonido`.

Toda la dramaturgia sonora pertenece al host/moderador.

## 3. Información mostrada

El participante puede ver:

- código de sala durante enrolamiento;
- avatar y alias;
- estado de conexión;
- rol (`Público`, `Jugador seleccionado`, `Jugador activo`);
- mensajes breves de espera;
- A/B/C/D cuando el servidor habilita una apertura;
- timer visual de la apertura;
- confirmación/estado de su respuesta.

No debe mostrar:

- enunciado de la pregunta;
- texto de las alternativas;
- respuesta correcta;
- contenido audiovisual propio del escenario principal.

## 4. Estados esperados

```text
ENROLAMIENTO
→ ESTÁS DENTRO
→ CLASIFICATORIA A-D
→ RESPUESTA RECIBIDA
→ ESPERA / PÚBLICO / JUGADOR SELECCIONADO
→ PREGUNTA DEL JUGADOR A-D (si corresponde)
→ CONSULTA AL PÚBLICO A-D (si corresponde)
→ ESPERA
```

## 5. Autoridad del servidor

El móvil no decide cuándo puede responder.

Debe obedecer:

- `opening_id`;
- `opening.allowed_answers`;
- duración y `opened_at` de la apertura;
- rol y elegibilidad recibidos por snapshot;
- `answer.ack` del servidor.

El 50:50 se refleja mediante `allowed_answers`: las alternativas eliminadas no deben renderizarse y el backend conserva la defensa adicional contra respuestas prohibidas.

## 6. Conectividad protegida

Fase 5 no modifica:

- token de participante;
- device ID persistente;
- WebSocket por sala;
- heartbeat cada 20 segundos;
- reconexión progresiva;
- recuperación por `/reconnect`;
- prevención de duplicados mediante identidad/token existentes;
- sincronización de rol y apertura desde el servidor.

## 7. Presentación visual

La referencia es el pulsador V3.1.4: simple, legible y centrado en la acción.

La adaptación V4 utiliza:

- encabezado `SALA PARTICIPATIVA / Pulsador interactivo`;
- enrolamiento compacto;
- avatar + alias;
- pantalla de espera simple;
- cuatro teclas A/B/C/D grandes;
- feedback visual, nunca sonoro;
- diseño adecuado a pantalla táctil y safe areas móviles.

Archivo de estilo: `online/static/phase5_mobile.css`.

## 8. Archivos de implementación

- `online/static/play.html`
- `online/static/play.js`
- `online/static/phase5_mobile.css`
- `online/tests/test_frontend_phase5.py`

## 9. Criterios de aceptación

Antes de `main`:

1. entrar a una sala desde varios teléfonos no genera ningún sonido;
2. abrir una clasificatoria no genera sonido en teléfonos;
3. pulsar A/B/C/D no genera sonido;
4. llamada, público y 50:50 no generan audio en teléfonos;
5. sólo los elegibles reciben A/B/C/D;
6. 50:50 renderiza únicamente alternativas permitidas;
7. reconexión recupera identidad y rol;
8. pasar a segundo plano y volver no crea duplicados;
9. el host mantiene su audio canónico independiente;
10. iOS y Android equivalentes conservan pulsación cómoda y feedback legible.

## 10. Regla para cambios futuros

No volver a introducir audio en el cliente participante por conveniencia, feedback o estética sin una decisión canónica explícita.

Si se desea mejorar feedback del móvil, hacerlo mediante jerarquía visual, texto, animación moderada o vibración sólo si se evalúa y aprueba explícitamente en el futuro; Fase 5 no implementa vibración.
