# CANON — Reconstrucción Frontend V4 · Desafío Millonario

Estado: **VIGENTE**

Fecha de fijación: 17 de agosto de 2026

Rama de trabajo: `v4-frontend-race`

Base estable: `main`

## 1. Propósito

Este documento fija el contrato de reconstrucción del frontend de V4. Su objetivo es trasladar fielmente la experiencia visual, escénica y audiovisual del producto histórico a la arquitectura web/multiusuario ya construida, sin rehacer el backend que actualmente resuelve salas, Internet, WebSockets, clasificación, roles, reconexión y temporización autoritativa.

Principio rector:

> **No reconstruir la lógica que ya funciona para solucionar un problema visual.**

La meta no es crear otra interfaz inspirada en Millonario. La meta es que V4 se sienta como la evolución web definitiva del mismo producto construido en V2/V3.

---

## 2. Jerarquía de fuentes maestras

Cuando exista una duda o contradicción, se aplicará esta jerarquía:

1. **`Quien quiere ser millonario FEB 2026.pptx`**: fuente maestra de estética, composición y dramaturgia audiovisual original; especialmente ritmo, entradas musicales y lenguaje visual del juego y comodines.
2. **V3.1.4 (`v3_1/`)**: fuente maestra de dinámica participativa y reglas de sala: enrolamiento, clasificatoria, selección, roles, rondas, comodines, temporizadores, público, reconexión y repetición.
3. **V2**: fuente maestra del menú inicial, administrador manual de preguntas, importación Excel y continuidad visual previa a la participación móvil.
4. **V4 actual (`online/`)**: fuente maestra de infraestructura web: FastAPI, acceso desde redes diferentes, WebSockets, autenticación del moderador, QR/URL pública, rate limiting, reconexión, despliegue y sincronización por servidor.

Una reinterpretación introducida en V4 no prevalece sobre una decisión canónica anterior salvo que este documento la declare explícitamente como mejora V4.

---

## 3. Elementos protegidos del chasis V4

La reconstrucción del frontend debe preservar, salvo defecto comprobado:

- FastAPI y rutas actuales necesarias para la operación web.
- WebSockets y sincronización servidor-cliente.
- Estado autoritativo del servidor para timers y respuestas.
- Acceso de participantes desde la misma red o redes distintas mediante Internet.
- Autenticación del moderador y su sesión.
- Identidad, token y reconexión de participantes.
- Capacidad objetivo de 30 participantes.
- Clasificatoria, ranking por corrección y tiempo del servidor.
- Roles de jugadores seleccionados y público.
- Comodines funcionales.
- Repetición conservando identidades/conexiones.
- Integración actual con Render.

No migrar lógica crítica al navegador sólo para simplificar la interfaz.

---

## 4. Contrato del flujo del moderador

Flujo definitivo:

```text
HOME PÚBLICA
    ↓
MODERADOR
    ↓
LOGIN
    ↓
MENÚ MILLONARIO
    ├── Crear sala participativa
    └── Editar preguntas
            ├── Administrador manual
            └── Importar banco desde Excel
    ↓
SALA / ENROLAMIENTO
    ↓
CLASIFICATORIA
    ↓
RESULTADOS
    ↓
2 JUGADORES CLASIFICADOS
    ↓
RONDA 1
    ↓
RONDA 2
    ↓
FINAL / REPETIR
```

### Home pública

Conservar la composición visual general V4 que funciona bien, con estos cambios:

- `Anfitrión` pasa a **`Moderador`** en toda la interfaz.
- `Moderador` debe ser un botón/acción claramente identificable.
- Eliminar el ingreso manual de código numérico de sala de la Home.
- No mostrar un QR operativo en la Home: la URL/QR real sólo existe al crear una sala.
- Mantener ATLAS únicamente como firma secundaria pequeña y discreta.

### Login

- Conservar autenticación existente.
- Cambiar textos `Anfitrión` por `Moderador`.
- No convertir el login en una escena del juego.
- No iniciar música durante el login o administración previa.

### Menú inicial

Eliminar el flujo `Mis bancos / Seleccionar / Crear sala` mientras sólo exista un banco operativo.

Recuperar el esquema V2/V3:

- **Crear sala participativa**.
- **Editar preguntas**.

`Editar preguntas` abre:

- **Administrador manual**.
- **Importar banco desde Excel**.

---

## 5. Sala de enrolamiento

La sala debe recuperar la composición de V3 y dejar de verse como dashboard SaaS.

### Columna izquierda

Debe concentrar controles del moderador:

- Código de sala.
- QR.
- Estado `Sala abierta`.
- Contador visible **Conectados: N / 30**.
- Selector de preguntas por jugador **1 / 3 / 5**.
- Botón **Cerrar sala e iniciar clasificación**.

Eliminar de la escena principal:

- `Copiar enlace` como control protagonista.
- `Finalizar partida` en el lobby.
- métricas duplicadas `Inscritos / Conectados / Respuestas`.
- card gigante `La sala está lista`.
- explicaciones administrativas que compitan con el escenario.

El backend puede conservar contadores técnicos internos de enrolados/conectados aunque visualmente sólo se muestre el contador útil de conectados.

### Centro

Debe quedar dedicado a los participantes que se van conectando:

- avatar + alias;
- grilla compacta;
- tamaño suficiente para visualizar simultáneamente un grupo amplio;
- el centro es escenario, no panel administrativo.

### Inicio audiovisual

La experiencia audiovisual comienza al crear/abrir la sala, mediante una interacción explícita del moderador que también sirve para desbloquear audio en el navegador.

---

## 6. Dinámica participativa canónica

### Clasificatoria

Todos los participantes elegibles responden una pregunta clasificatoria.

- Duración: **30 segundos**.
- Al pulsar `Cerrar sala e iniciar clasificación`, se cierran nuevos enrolamientos y comienza el proceso sin una pantalla manual intermedia innecesaria.
- Se muestran pregunta y A/B/C/D en la pantalla principal.
- Los móviles reciben A/B/C/D inmediatamente.
- El servidor recibe y ordena respuestas.
- Clasificación: respuesta correcta + velocidad medida por el servidor.
- Los dos mejores aciertos quedan preseleccionados.
- Si no hay dos aciertos, completar cupos con participantes disponibles para no bloquear la sesión.

### Resultado clasificatorio

Recuperar una escena dedicada:

- gráfica A/B/C/D;
- porcentajes y cantidades;
- identificación visual de respuesta correcta;
- transición posterior hacia los dos clasificados.

### Jugadores clasificados

Pantalla propia, no lista administrativa:

- dos participantes enfrentados visualmente;
- avatar + alias;
- confirmación clara del moderador.

Los demás **no quedan eliminados de la sesión**: permanecen conectados como público y vuelven a ser candidatos en una repetición/nueva clasificatoria.

---

## 7. Selector V4 de 1 / 3 / 5 preguntas

Esta es una mejora deliberada de V4 y no debe confundirse con la regla fija de cinco preguntas de V3.

El moderador selecciona antes de iniciar la clasificatoria:

- `1` pregunta por jugador;
- `3` preguntas por jugador;
- `5` preguntas por jugador.

El plan general será:

```text
1 clasificatoria
+ N preguntas jugador 1
+ N preguntas jugador 2
+ reserva disponible según la estrategia del plan
```

con `N ∈ {1, 3, 5}`.

El modo 5 debe conservar la experiencia completa equivalente a V3. El selector debe ser autoritativo en backend; no puede ser sólo una etiqueta visual.

Eliminar hardcodes de `5 preguntas` allí donde deban depender de N.

---

## 8. Escenas de ronda y pregunta

Cada estado necesita una **escena**, no sólo contenido distinto dentro de una card genérica.

Recuperar la secuencia:

```text
INTRO RONDA
→ PREGUNTA
→ BLOQUEO/REVELACIÓN
→ SIGUIENTE PREGUNTA
→ RESUMEN RONDA
→ INTRO SIGUIENTE RONDA / FINAL
```

### Intro de ronda

Debe mostrar de forma escénica:

- `RONDA 1` o `RONDA 2`;
- avatar/alias del jugador;
- N preguntas;
- tiempo por pregunta;
- botón `Comenzar ronda`.

### Pregunta

Recuperar el lenguaje visual V2/V3/PPT:

- fondo Millonario;
- pregunta protagonista;
- A/B/C/D en 2×2;
- azul/royal/plata/dorado;
- temporizador protagonista;
- comodines integrados visualmente como parte del juego;
- respuesta correcta en verde;
- respuesta elegida incorrecta en rojo;
- 50:50 ocultando/deshabilitando las dos alternativas eliminadas.

Evitar estética de dashboard, métricas SaaS o cards administrativas durante el juego.

---

## 9. Comodines

### 50:50

- Se aplica automáticamente.
- Elimina exactamente dos alternativas incorrectas.
- Debe reflejarse tanto en host como en el pulsador del jugador.
- El servidor sigue rechazando cualquier alternativa eliminada como defensa adicional.

### Llamada

- Ventana de **15 segundos**.
- Tratamiento audiovisual en la pantalla principal.
- No requiere participación del público.
- Al finalizar vuelve limpiamente a la pregunta.

### Consulta al público

- Ventana de **15 segundos**.
- Participan los usuarios con rol público.
- Los jugadores seleccionados quedan excluidos de la votación.
- Los móviles elegibles muestran A/B/C/D sólo durante la consulta.
- El servidor agrega las respuestas.
- La pantalla principal muestra una gráfica A/B/C/D con porcentajes/cantidades.
- Después se vuelve a la pregunta activa.

Regla de producto:

> **Una persona que no clasifica nunca abandona la sesión: permanece conectada como público, puede participar en Consulta al público y vuelve automáticamente a ser candidata en la siguiente clasificatoria.**

---

## 10. Contrato audiovisual

### Fuente maestra

La dramaturgia audiovisual se toma del PowerPoint `Quien quiere ser millonario FEB 2026.pptx` y se adapta al navegador sin alterar su intención. V3 es referencia complementaria, pero no debe usarse para eliminar ritmos presentes en el PPT original.

### Responsabilidad

**Sólo la pantalla del moderador reproduce audio.**

Los pulsadores móviles deben permanecer 100 % silenciosos.

No reproducir en móviles:

- intro;
- música de pregunta;
- transiciones;
- correcto/incorrecto;
- 50:50;
- llamada;
- público;
- sonidos al enrolarse.

### Política de reproducción

- Un único track de fondo activo a la vez.
- Efectos pueden superponerse sólo cuando sea intencional.
- Evitar que polling/snapshot vuelva a disparar el mismo cue.
- Usar ID/revisión de evento para idempotencia de audio.
- Precargar pistas críticas.
- Aplicar fade/stop donde corresponda antes de revelar respuesta.
- Mantener control `Silenciar` para el moderador.

### Ritmo base a reconstruir

```text
LOGIN / ADMINISTRACIÓN
→ silencio

CREAR SALA / LOBBY
→ intro / ambiente

CLASIFICATORIA
→ entrada/transición audiovisual
→ tensión de pregunta

RESULTADOS / CLASIFICADOS / INTRO DE RONDA
→ continuidad/transición según cue canónico

PREGUNTA
→ cue de entrada
→ música sostenida de pregunta

RESPUESTA BLOQUEADA
→ detener/fadear tensión
→ correcto o incorrecto

SIGUIENTE PREGUNTA
→ cue de entrada
→ música de pregunta

50:50
→ efecto breve

LLAMADA
→ cue/pista específica durante la ventana de 15 s

PÚBLICO
→ cue/pista específica durante la ventana de 15 s
→ gráfica
```

Los offsets/duraciones exactos del PPT deben documentarse al implementar la fase de audio, evitando sustituirlos por aproximaciones si se pueden recuperar del archivo fuente.

---

## 11. Contrato del móvil

El móvil vuelve al rol de V3.1.4: **Pulsador interactivo**, no segunda pantalla audiovisual del concurso.

Estados esperados:

```text
ENROLAMIENTO
→ ESTÁS DENTRO
→ CLASIFICATORIA A-D
→ RESPUESTA RECIBIDA
→ CLASIFICACIÓN FINALIZADA
→ ESPERA / PÚBLICO
→ CONSULTA AL PÚBLICO A-D (cuando corresponda)
→ ESPERA
```

Para jugadores seleccionados, mostrar únicamente los controles necesarios para su rol.

Principios:

- silencio absoluto;
- feedback visual claro;
- avatar + alias + conexión;
- reconexión sin crear un participante duplicado;
- recuperar correctamente rol/estado al volver de segundo plano;
- no mostrar contenido audiovisual que pertenezca al escenario del moderador.

---

## 12. Editor de preguntas e importación Excel

Recuperar en web las capacidades ya existentes en V2/V3.

### Administrador manual

Debe permitir:

- listar preguntas;
- seleccionar una pregunta;
- editar enunciado;
- editar A/B/C/D;
- seleccionar respuesta correcta;
- crear;
- duplicar;
- eliminar;
- reordenar;
- guardar cambios;
- validar límites/estructura antes de persistir.

### Importación Excel

- aceptar `.xlsx` según formato definido por el proyecto;
- validar estructura, filas y alternativas;
- entregar errores comprensibles;
- no reemplazar el banco si la validación falla;
- conservar estrategia de respaldo cuando corresponda.

La persistencia cloud definitiva puede tratarse por separado; no introducir PostgreSQL sólo para completar la reconstrucción visual si no es estrictamente necesario para esa fase.

---

## 13. Repetición

`Repetir juego` debe conservar:

- sala;
- identidad/tokens;
- conexiones WebSocket;
- alias;
- avatares.

Debe reiniciar:

- roles a público;
- clasificados;
- puntajes;
- comodines;
- respuestas;
- plan de preguntas.

Después comienza una **nueva clasificatoria** sin pedir a los participantes volver a escanear el QR.

---

## 14. Fases de ejecución

### Fase 0 — Contrato y rama

- [x] Crear rama `v4-frontend-race` desde `main`.
- [x] Crear este documento canónico.
- [ ] No tocar todavía producción.

### Fase 1 — Flujo administrativo

- [ ] Home: `Moderador`.
- [ ] Eliminar ingreso manual de código.
- [ ] Conservar login.
- [ ] Eliminar `Mis bancos`.
- [ ] Recuperar menú V3.

### Fase 2 — Lobby V3 en chasis V4

- [ ] QR/código/contador/selector 1-3-5/acción en columna izquierda.
- [ ] Participantes como foco central.
- [ ] Eliminar controles y métricas redundantes.
- [ ] Inicio de audio exclusivamente en host.

### Fase 3 — Clasificatoria y selección

- [ ] Escena clasificatoria fiel.
- [ ] 30 s autoritativos.
- [ ] gráfica de resultados.
- [ ] pantalla de dos clasificados.

### Fase 4 — Rondas y preguntas

- [ ] Intro de ronda.
- [ ] pregunta V3/PPT.
- [ ] revelación correcta/incorrecta.
- [ ] resumen de ronda/final.

### Fase 5 — Audio canónico

- [ ] Extraer/documentar cues exactos del PPT.
- [ ] Integrar cues sólo en host.
- [ ] eliminar audio móvil.
- [ ] evitar duplicados y solapamientos no deseados.

### Fase 6 — Selector 1/3/5

- [ ] Parametrizar backend.
- [ ] parametrizar frontend/textos.
- [ ] pruebas de los tres modos.

### Fase 7 — Editor + Excel

- [ ] administrador manual web.
- [ ] importación/validación Excel.
- [ ] persistencia segura acorde al MVP.

### Fase 8 — Comodines y público

- [ ] 50:50 extremo a extremo.
- [ ] llamada 15 s.
- [ ] público 15 s + gráfica.
- [ ] retorno correcto a pregunta.

### Fase 9 — Replay y continuidad

- [ ] repetir sin QR.
- [ ] roles y estado reiniciados.
- [ ] nueva clasificatoria.

### Fase 10 — Pulido

- [ ] fullscreen/16:9.
- [ ] responsive.
- [ ] tipografía/espaciado.
- [ ] animaciones moderadas.
- [ ] precarga audiovisual.
- [ ] cero saltos de layout relevantes.

### Fase 11 — QA y producción

- [ ] suite existente sin regresiones.
- [ ] pruebas nuevas 1/3/5.
- [ ] 30 participantes / misma IP.
- [ ] reconexión.
- [ ] audio sólo host.
- [ ] 50:50.
- [ ] público.
- [ ] llamada.
- [ ] replay.
- [ ] Chrome desktop.
- [ ] móvil iOS/Android equivalente.
- [ ] fullscreen.
- [ ] validación Render/WebSocket.
- [ ] PR → `main` sólo después de aceptación visual y funcional.

---

## 15. Entregas de control

Para evitar una reconstrucción monolítica:

### Entrega A

Home + Moderador + Menú + Lobby.

### Entrega B

Clasificatoria + Resultados + Clasificados.

### Entrega C

Rondas + Preguntas + Comodines + Audio.

### Entrega D

1/3/5 + Editor + Excel + Replay + QA.

Cada entrega debe quedar operativa y revisable antes de avanzar.

---

## 16. Criterios de aceptación del producto óptimo

V4 estará lista cuando:

1. Un moderador pueda abrir una sesión desde web y participantes de redes distintas entren sin instalar software.
2. El recorrido visual recuerde inequívocamente al producto V2/V3/PPT y no a un dashboard SaaS genérico.
3. Cada estado principal tenga una escena propia y comprensible.
4. El audio reproduzca la dramaturgia original desde el host sin eco de teléfonos.
5. La clasificatoria permita que todos compitan y seleccione dos jugadores por corrección/velocidad.
6. Los no clasificados permanezcan activos como público.
7. 50:50, llamada y público funcionen extremo a extremo.
8. El moderador pueda elegir 1, 3 o 5 preguntas por jugador.
9. La sesión pueda repetirse sin volver a escanear QR.
10. El editor/importador vuelva a estar disponible sin deteriorar el backend web.
11. No haya regresiones en conectividad, autenticación, reconexión ni temporización autoritativa.
12. `main` sólo reciba la reconstrucción después de validación visual, funcional y de pruebas.

---

## 17. Regla de continuidad para futuras sesiones/agentes

Antes de modificar frontend, dinámica o audio de V4, leer este archivo completo.

No inferir decisiones por estética moderna, similitud de marca o arquitectura de otros proyectos.

ATLAS, cuando aparezca en Desafío Millonario, es sólo la firma/branding autorizado para esta aplicación salvo una decisión posterior explícita. No usar el proyecto Atlas Learning Hub como fuente para rediseñar la arquitectura o el juego.

Si una propuesta contradice este canon, detener la implementación y documentar la discrepancia antes de modificar código.
