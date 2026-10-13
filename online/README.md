# Plataforma online de Desafío Millonario

Aplicación web independiente que reutiliza el motor validado de la edición de
escritorio. El anfitrión crea una sala desde el navegador y los participantes
ingresan mediante código o QR.

## Desarrollo

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\online\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn desafio_online.app:app `
  --app-dir .\online\src --reload
```

Abra `http://127.0.0.1:8000`. La contraseña local inicial es `desafio` y puede
cambiarse con `ADMIN_PASSWORD`.

## Principios de arquitectura

- `v3_1/` permanece como referencia estable y no se modifica.
- El dominio reutilizable (`model`, `storage`, `RoomManager`) se importa desde
  `v3_1/src` sin depender de PySide6/QML.
- La interfaz web y el registro multi-sala viven en `online/`.
- El estado es en memoria durante este primer hito y está encapsulado detrás de
  `RoomRegistry` para sustituirlo por PostgreSQL sin cambiar las rutas públicas.
- La ejecución inicial usa una sola instancia y un solo worker.

## Flujo de juego

El servidor conserva la máquina de estados de la experiencia original:

`lobby_open` → `qualifier_open` → `qualifier_results` →
`player_selection` → `round_intro` → `question_active` →
`answer_revealed` → `round_summary` → `session_summary`.

- La clasificatoria dura 30 segundos y acepta a todos los teléfonos inscritos.
- El ranking considera únicamente aciertos y usa el tiempo de recepción del
  servidor. Si faltan aciertos, los cupos se completan con participantes
  disponibles.
- El plan estándar usa exactamente 12 preguntas: una clasificatoria, cinco
  para cada jugador y una de reserva.
- Cada pregunta de ronda dura 45 segundos. Los comodines llamada y público
  duran 15 segundos y pausan el tiempo restante de la pregunta.
- Los teléfonos no reciben el texto de la pregunta ni sus alternativas: sólo
  el pulsador A–D cuando su rol y el estado lo permiten.
- Repetir conserva el código, las conexiones, los tokens y los alias, devuelve
  los roles a público y crea un nuevo plan aleatorio.

## Diferencias propias de la versión web

- El jugador activo responde desde su teléfono; la pantalla del anfitrión
  presenta la pregunta, las alternativas, el tiempo y la revelación.
- El audio necesita una interacción del anfitrión para cumplir las políticas
  de los navegadores. Desde ese gesto, las pistas siguen el estado de la sesión
  y se evita superponer música de fondo.
- La aplicación de escritorio usa una ventana PySide/QML y la web usa una sala
  autoritativa en FastAPI con snapshots y reconexión por WebSocket.
- Las salas viven en memoria en esta etapa. Por eso Render debe mantener una
  sola instancia y un solo worker; reiniciar el servicio cierra las salas que
  estaban en curso.

## Pruebas

Desde la raíz del repositorio:

```powershell
python -m pytest .\online\tests -q
```

La suite cubre creación y enrolamiento, clasificatoria y ranking, selección y
fallback seguro, dos rondas completas, los tres comodines, temporizadores,
respuestas tardías, roles, reconexión, repetición, plan de 12 preguntas y las
rutas públicas existentes.

## Render

El archivo `render.yaml` define el servicio web. En Render debe configurarse
`ADMIN_PASSWORD` como secreto antes del primer uso.
