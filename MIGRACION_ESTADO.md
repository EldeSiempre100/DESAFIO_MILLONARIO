# Migración Desafío Millonario — completada

Fecha: 2026-10-18.

## Resultado e integridad

- Origen: `EldeSiempre100/QUIEN_QUIERE_SER_`, main `13c304f81aa0b3f47f02e6bf75fadd6a6bed2456`, 176 archivos. Solo lectura; privacidad privada.
- Destino: `EldeSiempre100/DESAFIO_MILLONARIO`, main.
- Se completaron las diez rutas pendientes mediante los cinco blobs ya existentes en el destino, sin retransmitir sus bytes. Commit: `5755d05ed7c9f5fec9e33e8b4412bb991a6c910b`.
- Total: 169 archivos = 168 rutas depuradas del origen + este informe.
- 167 archivos coinciden con el origen por ruta, tamaño y SHA Git. Única adaptación: `render.yaml`.
- Los 169 archivos de la copia local pública fueron cotejados byte a byte mediante tamaño y SHA Git, antes y después de las pruebas: ninguna diferencia. Incluye los 39 binarios y plantillas Excel.
- Se conservaron las versiones presentes en el árbol depurado. No se transfirió el historial privado ni se utilizó force-push.

## Archivos incorporados en el cierre

En `assets/` y también en `v3_1/assets/`:
- `audio/audience.wav` — 79e69f24e8ed6f69ceb3506c099e84a9a1d5d3b7
- `audio/question_music.mp3` — 42fb915793d0bf8f83681981620267903bba1bad
- `images/game_background_v2.png` — 2d32f505ecf97ea96d5725951e2250bd41e5bb31
- `images/game_background_v3_clean.png` — 547477bd27099f705611209e77196ae12abcf979
- `images/menu_background_v2.png` — 11438532fa4209bf5bcabf3df5df5ab4306a0a8f

## Exclusiones autorizadas

Documentos Word/PowerPoint:
- Ficha_tecnica_V1_aplicacion_preguntas.docx
- Quien quiere ser millonario FEB 2026.pptx
- docs_v3/Informe_y_Guia_Construccion_V3_1_Desafio_Millonario.docx
- docs_v3/Informe_y_Guia_Construccion_V3_1_Desafio_Millonario_con_Anexo_Red_y_Pulsadores.docx
- v3_1/docs/Guia_Construccion_V3_1.docx

Capturas de diagnóstico con datos de usuario/sesión local:
- v3_1/docs/errores_reportados/NUEVO ERROR 1.jpeg
- v3_1/docs/errores_reportados/NUEVO ERROR 2.png
- v3_1/docs/errores_reportados/error pulsador web.jpg

## Adaptación deliberada de Render

`render.yaml`: únicamente se cambió la rama de `v4-online` a `main`. Se conservan:
- Un servicio web Python.
- Build: `pip install -r online/requirements.txt`
- Inicio: `uvicorn desafio_online.app:app --app-dir online/src --host 0.0.0.0 --port $PORT --workers 1`
- Salud: `/health`
- `ENVIRONMENT=production`, `ADMIN_PASSWORD` con `sync: false`, `MAX_PARTICIPANTS=30`.

## Pruebas realmente ejecutadas

Entorno temporal Windows, Python 3.12.10. No se reutilizó el venv Linux anterior; su ZIP no estaba en la ruta equivalente de este entorno. Se descargó únicamente una copia pública del destino para validación.

Versiones ejecutadas: PySide6 6.12.0, FastAPI 0.145.0, Uvicorn 0.54.0, Starlette 1.8.0, Pydantic 2.14.1, pytest 9.1.1, httpx 0.28.1, websockets 16.1.1, segno 1.6.6.

| Comprobación | Resultado |
| --- | --- |
| AST de todos los Python | 68 archivos correctos |
| `tests/`, proceso independiente | 24 passed |
| `v3_1/tests/`, proceso independiente | 23 passed |
| `online/tests/`, proceso independiente | 99 passed |
| Total | 146 passed, 0 fallidas |
| Ambas aplicaciones de escritorio | Arranque real offscreen, carga QML y cierre automático correctos |
| `pip check` | No broken requirements found |
| FastAPI/Uvicorn real, modo producción | Arranque correcto en localhost |
| `/health` | HTTP 200, status ok |
| Autenticación y creación de sala | Correctas |
| `/`, `/admin`, `/host/{codigo}`, `/join/{codigo}` | HTTP 200 |
| Recursos `/assets` y `/media` | 37 archivos servidos y cotejados byte a byte |
| WebSocket real de participante | Snapshot inicial y heartbeat correctos |
| Integridad después de pruebas | 169 archivos sin diferencias de hash |

Las pruebas online incluyen flujos del juego, frontend, banco, persistencia, comodines, repetición y WebSockets. La comprobación adicional del servidor utilizó contraseña temporal aleatoria. En producción la cookie es Secure: para probar sobre HTTP local se envió expresamente la cookie en el cliente de QA; no se modificó el código de autenticación.

## Hallazgos y límites

- No se identificaron fallas funcionales introducidas por la migración ni fallas preexistentes en las suites ejecutadas.
- Advertencia con las dependencias actuales: Starlette depreca el uso de httpx en TestClient y sugiere httpx2. No impide las 146 pruebas. Las restricciones amplias de versiones ya estaban en el origen.
- Qt emitió mensajes del entorno Windows sobre codificadores AV1/HEVC no disponibles; ambas aplicaciones finalizaron correctamente. No constituye una alteración de recursos.
- La instalación temporal tuvo intentos iniciales incompletos; los resultados anteriores corresponden a las ejecuciones posteriores con las dependencias disponibles.
- No se realizó revisión visual manual en navegador ni prueba desde un teléfono por Internet. No se ha desplegado un servicio público.
- En producción, sin QUESTION_BANK_PATH, el banco usa el archivo del repositorio en modo lectura. Para edición persistente se necesita configurar una ruta con almacenamiento durable; no es un defecto de migración.

## Pendientes concretos para publicar

1. Crear en Render el servicio/Blueprint conectado a este repositorio y su rama main.
2. Configurar ADMIN_PASSWORD con una contraseña propia.
3. Desplegar y comprobar /health bajo HTTPS.
4. Comprobar inicio de sesión, creación de sala, QR y conexión de participantes desde otro dispositivo, WebSockets seguros y audio en el navegador.
5. Si se requiere editar y conservar el banco en producción, configurar QUESTION_BANK_PATH sobre almacenamiento persistente antes de usar el editor.

GitHub Pages por sí solo no ejecuta FastAPI ni WebSockets; la aplicación requiere el servicio web.

Repositorio: https://github.com/EldeSiempre100/DESAFIO_MILLONARIO
