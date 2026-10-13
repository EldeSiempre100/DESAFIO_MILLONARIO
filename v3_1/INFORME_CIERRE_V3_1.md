# Informe de cierre — Millonario educativo V3.1

Fecha: 29 de julio de 2026.

## Resultado

Se construyó una V3.1 participativa e independiente. La V2 continúa disponible
como producto estable en `release\Millonario_Educativo_V2`.

La aplicación de escritorio mantiene la experiencia audiovisual y actúa como
anfitrión. Los teléfonos funcionan únicamente como pulsadores mediante una
página local, sin instalar aplicaciones y sin depender de Internet.

## Funciones terminadas

- Sala local con código y QR para un máximo oficial de 30 participantes.
- Alias validados, cupo controlado, reconexión y tokens individuales.
- Pregunta clasificatoria abierta a todo el público.
- Cierre por servidor, rechazo de respuestas tardías y bloqueo de duplicados.
- Porcentajes de respuestas y primeros cuatro aciertos ordenados por el servidor.
- Selección manual de dos participantes por el anfitrión.
- Dos rondas consecutivas de cinco preguntas; ambos participantes son ganadores.
- Consulta con el público usando los teléfonos que continúan en la sala.
- Comodines 50:50, llamada y público, con tres usos por ronda y máximo uno de
  cada tipo por pregunta.
- Temporizadores de 45 segundos para preguntas y 15 segundos para llamada y
  consulta al público.
- Plan exacto de 12 preguntas: 1 clasificatoria, 5 + 5 de juego y 1 reserva.
- Editor manual y carga mediante la plantilla Excel heredados de V2.
- Persistencia de eventos y estado de la sesión en archivos locales.
- Cliente móvil HTML/CSS/JavaScript incorporado al paquete y totalmente offline.
- Registro de errores de inicio en `data\runtime\startup_error.log`.

## Validación realizada

- 42 pruebas automatizadas superadas.
- Ensayo de 36 intentos de ingreso: 30 aceptados y 6 rechazados por cupo.
- Ráfaga de 30 respuestas, control de duplicados y respuestas tardías.
- Flujo completo del controlador: clasificatoria, selección, dos rondas y final.
- Prueba HTTP y WebSocket sobre un servidor Uvicorn real.
- Control visual de menú, lobby, clasificatoria, resultados, selección, ronda y
  pulsador móvil.
- Ejecutable compilado con Nuitka y Qt/PySide6.
- Prueba portable superada desde una copia temporal fuera del proyecto: el EXE
  inició, publicó `/health` y sirvió correctamente la página móvil.

## Uso desde un pendrive

1. Copiar completa la carpeta `release\Millonario_Educativo_V3_1`.
2. Mantener todas sus subcarpetas y archivos juntos.
3. Conectar el laptop anfitrión y los teléfonos a la misma red Wi-Fi privada.
4. Ejecutar `MillonarioEducativoV3_1.exe`.
5. En el primer inicio, si Windows Firewall consulta, habilitar únicamente
   **Redes privadas**.
6. Crear la sala y pedir a los participantes que escaneen el QR.
7. Cerrar el juego antes de extraer el pendrive.

Es técnicamente viable ejecutarlo desde un pendrive con permisos de escritura.
Las sesiones y el QR temporal se guardan dentro de `data`. El router debe
permitir comunicación entre clientes; algunas redes de invitados activan
aislamiento y bloquean esta función. No debe copiarse solamente el EXE.

## Continuación manual

Desde la raíz del proyecto, con Python 3.12 y el entorno `.venv` disponible:

```powershell
.\.venv\Scripts\python.exe .\v3_1\main.py
.\.venv\Scripts\python.exe -m pytest -q
.\v3_1\tools\build_v3_1.ps1
.\v3_1\tools\test_portable_v3_1.ps1
```

Los archivos principales son:

- `v3_1\qml\Main.qml`: interfaz de escritorio.
- `v3_1\src\millonario_v3\participative_controller.py`: integración del juego.
- `v3_1\src\millonario_v3\session.py`: flujo y planificación de preguntas.
- `v3_1\src\millonario_v3\participation`: sala, API, WebSocket y persistencia.
- `v3_1\mobile`: interfaz de los teléfonos.
- `v3_1\tests`: pruebas automatizadas.
- `v3_1\tools`: construcción y validación portable.

Antes de modificar el flujo, ejecutar las pruebas. Después de cualquier cambio,
repetir el build y la prueba portable. La V2 no debe editarse para implementar
mejoras de V3.1 o versiones posteriores.

## Alcances conocidos

- El ejecutable no está firmado digitalmente; SmartScreen puede advertir sobre
  aplicaciones nuevas o de baja reputación.
- La primera apertura del servidor puede generar la consulta de Firewall.
- La sala requiere una red local que permita tráfico directo entre dispositivos.
- La capacidad oficial validada para esta versión es de 30 participantes.
- Logo, música e identidad se mantienen por el alcance privado y educativo
  definido para el proyecto; no se recomienda distribución pública.

## Corrección posterior de compatibilidad móvil

El 29 de julio de 2026 se corrigió el enrolamiento desde Chrome móvil sobre una
dirección HTTP de red local. En ese contexto `crypto.randomUUID()` no está
disponible en algunos navegadores, lo que producía el mensaje «No fue posible
comunicarse con la sala». El cliente ahora genera una identidad compatible
mediante `crypto.getRandomValues()` y mantiene un último mecanismo alternativo
para navegadores antiguos.

La corrección se comprobó accediendo por una IP LAN en contexto no seguro:
`randomUUID` apareció como no disponible y el enrolamiento terminó correctamente
en el estado «Estás dentro / Conectado».

## Revisión V3.1.1 — acceso simplificado

Después de nuevas pruebas en teléfonos se eliminó la dependencia del código de
sala en la dirección web. Cada ejecutable aloja una sola sala activa, por lo que
el QR abre directamente:

```text
http://IP-DEL-LAPTOP:PUERTO/
```

El código de cuatro dígitos continúa visible como referencia del anfitrión, pero
ya no interviene en la ruta, en las llamadas HTTP ni en el WebSocket. Los enlaces
anteriores con `/sala/1234` redirigen a la entrada simple.

También se incorporaron:

- recuperación automática si un teléfono pierde su token;
- descarte de identidades almacenadas que pertenecen a otra sesión;
- versión en los archivos JavaScript y CSS para impedir que Chrome reutilice
  una copia antigua;
- reconexión después de recargar sin crear un segundo participante.

La prueba LAN se ejecutó mediante HTTP sin Internet y sin contexto seguro:
apertura en la raíz, enrolamiento, WebSocket y reconexión tras recargar fueron
correctos.

## Revisión V3.1.2 — timing y continuidad del público

La pregunta clasificatoria tiene dos momentos explícitos:

1. **Vista previa:** la pregunta y las cuatro respuestas quedan visibles en la
   pantalla principal; los teléfonos muestran «Observa la pregunta» y todavía
   no presentan A–D.
2. **Empezar votación:** el anfitrión activa manualmente los pulsadores y comienza
   el conteo de 20 segundos.

También se corrigió el estado de teléfonos que habían respondido o que perdían
momentáneamente el WebSocket. Al finalizar la clasificación todos abandonan la
pantalla «Respuesta recibida». Después de seleccionar dos participantes, los
demás muestran «Sigues participando» y permanecen habilitados para Consulta con
el público.

Se validaron tres teléfonos simultáneos, el envío del evento de selección a
todos, la recuperación del rol mediante snapshot y la reconexión cuando el
navegador vuelve desde segundo plano.

## Revisión V3.1.3 — clasificación directa y repetición

El botón «Cerrar sala e iniciar clasificación» ejecuta ahora todo el inicio:

- cierra nuevos enrolamientos;
- muestra la pregunta y alternativas en la pantalla principal;
- activa A–D inmediatamente en todos los teléfonos;
- inicia automáticamente una cuenta regresiva de 30 segundos;
- cierra la votación y presenta el gráfico al agotarse el tiempo.

Se eliminaron el botón intermedio de apertura, «Cerrar ahora» y la pregunta de
desempate. La clasificación conserva únicamente los dos primeros aciertos. Si
no existen dos, completa los cupos con participantes disponibles para evitar que
el juego quede bloqueado. La pantalla siguiente presenta solo esos dos nombres,
preseleccionados, para confirmación del anfitrión.

En el cierre se agregó «Repetir juego». La misma sala se reabre, conserva tokens
y teléfonos conectados, restablece todos los roles a público y genera un nuevo
plan de preguntas. No es necesario escanear nuevamente el QR.

Durante las rondas los teléfonos del público permanecen conectados en espera.
Solo reciben A–D durante los 15 segundos del comodín Consulta con el público;
los dos jugadores seleccionados quedan excluidos.

## Compilación portable final V3.1.3

El 30 de julio de 2026 se generó y validó la carpeta portable definitiva:

```text
release\Millonario_Educativo_V3_1
```

Resultados de cierre:

- versión de producto y archivo: **3.1.3.0**;
- 46 pruebas automatizadas superadas;
- prueba de ejecución portable superada desde una copia temporal independiente;
- 2.695 archivos, con un tamaño total de **243,58 MiB**;
- las tres capturas de errores reportadas se conservaron en `errores`;
- SHA-256 de `MillonarioEducativoV3_1.exe`:
  `AAA75EB4FA82767D76C1F683C03C5C4BED690644CAE313A7C646C3EB1043203A`.

La V2 permaneció intacta. Su ejecutable conserva el SHA-256:
`762C985239596A3E0F2EFCB9AEE60CCC93C5739745DC60334DADD639E602EF5B`.

Para usar la entrega desde un pendrive se debe copiar la carpeta completa, sin
extraer ni mover únicamente el archivo EXE. La red local puede funcionar sin
Internet, siempre que el computador y los teléfonos estén conectados a la misma
red y el Firewall de Windows permita el acceso del ejecutable a redes privadas.

## Revisión V3.1.4 — pulsador genérico y avatares

El 30 de julio de 2026 se desacopló la identidad visual del pulsador móvil del
juego principal. La página de los teléfonos utiliza ahora los textos «Sala
participativa» y «Pulsador interactivo», además de una paleta neutral azul y
turquesa. La lógica A–D, la red local y todos los eventos de V3.1.3 se
mantuvieron sin cambios.

Durante el enrolamiento cada persona puede elegir una de ocho personalidades:
Explorador, Estratega, Creativo, Curioso, Optimista, Sereno, Entusiasta y
Estrella. Son iconos Unicode incorporados, por lo que funcionan sin Internet y
no aumentan materialmente el tamaño de la aplicación.

El avatar:

- queda almacenado junto al alias y la identidad del teléfono;
- se recupera después de recargar o reconectar;
- puede cambiarse al recuperar la participación desde el mismo dispositivo;
- aparece en el listado de enrolados, la selección de jugadores y el cierre.

Resultados de la compilación:

- versión de producto y archivo: **3.1.4.0**;
- 47 pruebas automatizadas superadas;
- sintaxis del cliente móvil validada;
- revisión visual a tamaño de teléfono superada;
- prueba de ejecución portable superada;
- 2.697 archivos, con un tamaño total de **243,76 MiB**, incluida la vista
  previa del pulsador;
- SHA-256 de `MillonarioEducativoV3_1.exe`:
  `6522C30AE1217219462AF24797B1A98243ED7070D095505E75AB032C53F4D870`.

La V2 permanece intacta y conserva su SHA-256:
`762C985239596A3E0F2EFCB9AEE60CCC93C5739745DC60334DADD639E602EF5B`.
