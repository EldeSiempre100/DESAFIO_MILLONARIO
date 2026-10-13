const code = location.pathname.split("/").filter(Boolean).pop();
const letters = ["A", "B", "C", "D"];
let snapshot = null;
let busy = false;
let timerFrame = null;
let hostAudioStarted = false;

const byId = (id) => document.getElementById(id);
const gameAudio = new window.GameAudio(byId("soundButton"), {
  storageKey: "desafio:host-sound",
  musicOnEnable: () => backgroundForState(snapshot?.state),
  autoEnabled: true,
});

function errorMessage(payload, fallback) {
  const detail = payload?.detail;
  return detail?.message || (typeof detail === "string" ? detail : fallback);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (response.status === 401) {
    location.replace("/admin");
    throw new Error("Sesión finalizada");
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(errorMessage(payload, "No fue posible completar la acción."));
  return payload;
}

function node(tag, className = "", text = "") {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text) item.textContent = text;
  return item;
}

function actionButton(label, path, body = null, className = "button", disabled = false) {
  const button = node("button", className, label);
  button.type = "button";
  button.disabled = disabled;
  button.addEventListener("click", () => {
    gameAudio.enable(backgroundForState(snapshot?.state));
    perform(path, body);
  });
  return button;
}

function questionCountLabel(total) {
  const value = Number(total || 0);
  return value === 1 ? "1 pregunta" : `${value} preguntas`;
}

function renderParticipants(participants) {
  const list = byId("participantList");
  list.replaceChildren();
  if (!participants.length) {
    list.append(node("p", "muted participants-empty", "Aún no hay participantes."));
    return;
  }
  participants.forEach((participant) => {
    const item = node("div", `participant${participant.role === "selected" ? " selected-player" : ""}`);
    item.append(node("span", "participant-avatar", participant.avatar_symbol));
    item.append(node("span", "participant-name", participant.alias));
    if (participant.role === "selected") item.append(node("span", "role-badge", "JUGADOR"));
    const presence = node("span", `presence${participant.connected ? " online" : ""}`);
    presence.title = participant.connected ? "Conectado" : "Sin conexión";
    item.append(presence);
    list.append(item);
  });
}

function renderTimer(opening) {
  cancelAnimationFrame(timerFrame);
  const timer = byId("hostTimer");
  if (!opening || opening.status === "paused") {
    timer.classList.add("hidden");
    return;
  }
  timer.classList.remove("hidden");
  const openedAt = Date.parse(opening.opened_at);
  const duration = Number(opening.duration_ms || 0);
  const tick = () => {
    const remaining = Math.max(0, duration - (Date.now() - openedAt));
    byId("hostTimerValue").textContent = String(Math.ceil(remaining / 1000));
    timer.classList.toggle("urgent", remaining <= 5000);
    if (remaining > 0) timerFrame = requestAnimationFrame(tick);
  };
  tick();
}

function renderAnswers(parent, question, result = null) {
  const grid = node("div", "answer-preview v3-answer-grid");
  question.answers.forEach((answer, index) => {
    const hidden = question.hidden_indices?.includes(index);
    const classes = ["answer-line", "v3-answer"];
    if (hidden) classes.push("eliminated");
    if (result && index === result.correct_index) classes.push("correct");
    if (result && index === result.selected_index && index !== result.correct_index) classes.push("incorrect");
    const line = node("div", classes.join(" "));
    line.dataset.answer = letters[index];
    line.append(node("strong", "answer-letter-badge", letters[index]));
    line.append(node("span", "answer-copy", hidden ? "" : answer));
    grid.append(line);
  });
  parent.append(grid);
}

function renderDistribution(parent, results, title = "Distribución de respuestas") {
  if (!results) return;
  parent.append(node("h3", "distribution-title", title));
  const list = node("div", "results-list");
  letters.forEach((letter, index) => {
    const row = node("div", `result-row${index === results.correct_index ? " correct" : ""}`);
    row.append(node("span", "result-letter", letter));
    const track = node("div", "result-track");
    const fill = node("div", "result-fill");
    fill.style.width = `${results.percentages?.[index] || 0}%`;
    track.append(fill);
    row.append(
      track,
      node("span", "result-value", `${results.counts?.[index] || 0} · ${results.percentages?.[index] || 0}%`),
    );
    list.append(row);
  });
  parent.append(list);
}

function renderVerticalDistribution(parent, results) {
  const grid = node("div", "qualifier-bars");
  letters.forEach((letter, index) => {
    const percentage = Number(results.percentages?.[index] || 0);
    const count = Number(results.counts?.[index] || 0);
    const column = node("div", `qualifier-bar-column${index === results.correct_index ? " correct" : ""}`);
    column.append(node("strong", "qualifier-bar-letter", letter));
    const chart = node("div", "qualifier-bar-track");
    const fill = node("div", "qualifier-bar-fill");
    fill.style.height = `${Math.max(0, Math.min(100, percentage))}%`;
    chart.append(fill);
    column.append(chart);
    column.append(node("span", "qualifier-bar-value", `${percentage}% · ${count}`));
    grid.append(column);
  });
  parent.append(grid);
}

function renderLobby(data) {
  renderTimer(null);
  const startButton = byId("lobbyStartButton");
  startButton.disabled = busy || data.enrolled < 2;
  byId("roomMessage").textContent = data.enrolled < 2
    ? "Se requieren al menos dos participantes para iniciar la clasificación."
    : "La sala está lista. Cuando quieras, cierra el enrolamiento e inicia la clasificación.";
}

function renderQualifier(content, data) {
  const question = data.qualifier;
  const scene = node("section", "v3-scene qualifier-scene");
  const card = node("div", "v3-scene-card qualifier-card");
  const heading = node("div", "qualifier-heading");
  heading.append(node("h1", "scene-title-gold", "PREGUNTA CLASIFICATORIA"));
  card.append(heading);

  const questionPanel = node("div", "v3-question-panel");
  questionPanel.append(node("h2", "", question.prompt));
  card.append(questionPanel);
  renderAnswers(card, question);
  card.append(node(
    "p",
    "qualifier-response-count",
    `Respuestas recibidas: ${data.answers_received} / ${data.enrolled}`,
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(question.opening);
}

function renderQualifierResults(content, data) {
  const results = data.qualifier_results;
  const scene = node("section", "v3-scene qualifier-results-scene");
  const card = node("div", "v3-scene-card qualifier-results-card");
  card.append(node("h1", "scene-title", "RESULTADO DE LA CLASIFICACIÓN"));
  renderVerticalDistribution(card, results);
  card.append(node(
    "p",
    "scene-support-copy",
    "La respuesta correcta queda destacada. Los aciertos más rápidos ya están preseleccionados.",
  ));
  card.append(actionButton(
    "Continuar con los 2 jugadores",
    `/api/games/${code}/selection/start`,
    null,
    "classic-flow-button",
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function renderSelection(content, data) {
  const participants = data.selection?.participants || [];
  const preselected = data.selection?.preselected_ids || [];
  const selectedPeople = preselected
    .map((participantId) => participants.find((person) => person.participant_id === participantId))
    .filter(Boolean);
  const fallback = selectedPeople.length === 2 ? selectedPeople : participants.slice(0, 2);
  const selectedIds = fallback.map((person) => person.participant_id);

  const scene = node("section", "v3-scene selection-scene");
  const card = node("div", "v3-scene-card selection-card");
  card.append(node("h1", "scene-title", "JUGADORES CLASIFICADOS"));
  card.append(node(
    "p",
    "scene-support-copy",
    "Los dos primeros aciertos se ordenan por el tiempo registrado en el servidor.",
  ));

  const grid = node("div", "classified-grid");
  fallback.forEach((person, index) => {
    const playerCard = node("div", "classified-player-card");
    playerCard.append(node("span", "classified-avatar", person.avatar_symbol || "●"));
    playerCard.append(node("strong", "classified-name", person.alias));
    const time = person.elapsed_ms == null
      ? "Cupo completado por disponibilidad"
      : `${(person.elapsed_ms / 1000).toFixed(2)} segundos`;
    playerCard.append(node("span", "classified-time", `${index + 1} · ${time}`));
    grid.append(playerCard);
  });
  card.append(grid);
  card.append(actionButton(
    "Confirmar los 2 jugadores",
    `/api/games/${code}/players/confirm`,
    { participant_ids: selectedIds },
    "classic-flow-button",
    selectedIds.length !== 2,
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function renderRoundIntro(content, data) {
  const round = data.round;
  const player = round.active_player;
  const scene = node("section", "v3-scene round-intro-scene");
  const card = node("div", "v3-scene-card round-intro-v3-card");
  card.append(node("h1", "scene-title-gold", `RONDA ${round.round_number}`));
  card.append(node("span", "round-intro-avatar", player.avatar_symbol || "●"));
  card.append(node("h2", "round-player-name", player.alias));
  card.append(node(
    "p",
    "round-intro-copy",
    `${questionCountLabel(round.question_total)} · 45 segundos por pregunta`,
  ));
  card.append(node("p", "round-intro-copy", "3 usos de cada comodín disponibles"));
  card.append(actionButton(
    "Comenzar ronda",
    `/api/games/${code}/rounds/start`,
    null,
    "classic-flow-button",
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function renderLifelines(parent, data) {
  const lifelines = data.lifelines;
  const stack = node("div", "v3-lifeline-stack");
  const definitions = [
    ["fifty", "50:50", null],
    ["phone", "Llamada", "/media/images/phone.png"],
    ["audience", "Público", "/media/images/audience.png"],
  ];
  definitions.forEach(([name, label, icon]) => {
    const usedHere = lifelines.question_used?.includes(name);
    const remaining = lifelines.remaining?.[name] ?? 0;
    const button = node("button", `v3-lifeline-button lifeline-${name}`);
    button.type = "button";
    button.disabled = busy || usedHere || remaining < 1 || data.state !== "question_active";
    button.title = label;
    if (icon) {
      const image = document.createElement("img");
      image.src = icon;
      image.alt = "";
      button.append(image);
    } else {
      button.append(node("strong", "lifeline-fifty-copy", "50:50"));
    }
    button.append(node("span", "lifeline-remaining", String(remaining)));
    button.addEventListener("click", () => {
      gameAudio.enable("question");
      perform(`/api/games/${code}/lifelines/${name}`);
    });
    stack.append(button);
  });
  parent.append(stack);
}

function renderRegularQuestion(content, data) {
  const question = data.question;
  const round = data.round;
  const lifeline = data.lifelines.active;
  const scoreIndex = Math.max(0, Number(round.round_number || 1) - 1);
  const score = round.scores?.[scoreIndex] ?? 0;

  const scene = node("section", "v3-scene question-scene");
  scene.append(node(
    "div",
    "question-status-pill",
    `${round.active_player.alias} · Ronda ${question.round_number} · Pregunta ${question.question_number} de ${question.question_total} · Aciertos ${score}`,
  ));
  renderLifelines(scene, data);

  const playArea = node("div", "question-play-area");
  const questionPanel = node("div", "v3-question-panel regular-question-panel");
  questionPanel.append(node("h2", "", question.prompt));
  playArea.append(questionPanel);
  renderAnswers(playArea, question, question.result);

  let statusMessage = `Responde ${round.active_player.alias}`;
  if (lifeline === "phone") statusMessage = "Comodín de llamada en curso · 15 segundos";
  if (lifeline === "audience") statusMessage = "Consulta al público en curso · 15 segundos";
  if (data.state === "answer_revealed") {
    const result = question.result;
    statusMessage = result.timed_out
      ? "Tiempo finalizado"
      : (result.correct ? "¡Respuesta correcta!" : "Respuesta incorrecta");
  }
  playArea.append(node(
    "div",
    `question-status-message${data.state === "answer_revealed" ? (question.result?.correct ? " correct" : " incorrect") : ""}`,
    statusMessage,
  ));

  if (!lifeline && data.lifelines.audience_results) {
    const audienceBox = node("div", "audience-result-overlay");
    renderDistribution(audienceBox, data.lifelines.audience_results, "Resultado del público");
    playArea.append(audienceBox);
  }

  if (lifeline) {
    playArea.append(actionButton(
      "Cerrar comodín",
      `/api/games/${code}/lifelines/close`,
      null,
      "classic-flow-button compact-scene-action",
    ));
    renderTimer(data.lifelines.opening);
  } else if (data.state === "question_active") {
    renderTimer(question.opening);
  } else {
    renderTimer(null);
    const nextLabel = question.question_number === question.question_total
      ? "Ver resumen de ronda"
      : "Siguiente pregunta";
    playArea.append(actionButton(
      nextLabel,
      `/api/games/${code}/questions/next`,
      null,
      "classic-flow-button compact-scene-action",
    ));
  }

  scene.append(playArea);
  content.append(scene);
}

function renderRoundSummary(content, data) {
  const round = data.round;
  const index = round.round_number - 1;
  const score = round.scores?.[index] ?? 0;
  const scene = node("section", "v3-scene round-summary-scene");
  const card = node("div", "v3-scene-card round-summary-v3-card");
  card.append(node("h1", "scene-title", "RONDA FINALIZADA"));
  card.append(node("h2", "round-summary-name", round.active_player.alias));
  card.append(node("strong", "round-summary-score", `${score} de ${round.question_total}`));
  card.append(node("p", "scene-support-copy", "respuestas correctas"));
  card.append(actionButton(
    round.round_number === 1 ? "Presentar segunda ronda" : "Ver cierre",
    `/api/games/${code}/rounds/advance`,
    null,
    "classic-flow-button",
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function renderSessionSummary(content, data) {
  const scene = node("section", "v3-scene session-summary-scene");
  const card = node("div", "v3-scene-card session-summary-v3-card");
  card.append(node("h1", "scene-title", "¡TENEMOS DOS GANADORES!"));

  const grid = node("div", "session-players-grid");
  data.summary.players.forEach((player) => {
    const playerCard = node("div", "session-player-card");
    playerCard.append(node("span", "session-player-avatar", player.avatar_symbol || "●"));
    playerCard.append(node("strong", "session-player-name", player.alias));
    playerCard.append(node("span", "session-player-score", `${player.score} de 5 correctas`));
    grid.append(playerCard);
  });
  card.append(grid);
  card.append(actionButton(
    "Repetir juego",
    `/api/games/${code}/replay`,
    null,
    "classic-flow-button",
  ));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function renderClosed(content) {
  const scene = node("section", "v3-scene closed-scene");
  const card = node("div", "v3-scene-card round-summary-v3-card");
  card.append(node("h1", "scene-title", "EXPERIENCIA FINALIZADA"));
  card.append(node("p", "scene-support-copy", "La partida fue cerrada. Gracias por participar."));
  scene.append(card);
  content.append(scene);
  renderTimer(null);
}

function backgroundForState(state) {
  if (state === "lobby_open") return "intro";
  if (state === "qualifier_open" || state === "question_active") return "question";
  return null;
}

function syncAudio(data) {
  if (!gameAudio.enabled) return;
  const storageKey = `desafio:host:last-audio-event:${code}`;
  const eventId = Number(data.last_event?.id || 0);
  const previousId = Number(sessionStorage.getItem(storageKey) || 0);
  if (eventId > previousId) {
    const name = data.last_event.name;
    if (name === "answer_revealed") {
      gameAudio.stopMusic({ fadeMs: 260 });
      gameAudio.play(data.last_event.correct ? "correct" : "incorrect");
    } else if (name === "lifeline_fifty") {
      gameAudio.play("lifeline");
    } else if (name === "lifeline_started") {
      gameAudio.stopMusic({ fadeMs: 220 });
      gameAudio.play("lifeline");
      gameAudio.playVoice(data.last_event.lifeline === "phone" ? "call" : "audience");
    } else if (name === "lifeline_finished" || name === "question_started" || name === "qualifier_started") {
      gameAudio.startMusic("question");
    } else if (["qualifier_finished", "players_confirmed", "round_finished", "round_intro", "session_finished", "session_restarted"].includes(name)) {
      gameAudio.stopMusic({ fadeMs: 220 });
      gameAudio.play("transition");
    }
    sessionStorage.setItem(storageKey, String(eventId));
  }
  const background = backgroundForState(data.state);
  if (background && data.state !== "lifeline_active") gameAudio.startMusic(background);
  if (!background && !["answer_revealed", "lifeline_active"].includes(data.state)) {
    gameAudio.stopMusic({ fadeMs: 180 });
  }
}

function render(data) {
  snapshot = data;
  if (!hostAudioStarted) {
    hostAudioStarted = true;
    gameAudio.enable(backgroundForState(data.state));
  }
  const stageCard = byId("stageCard");
  stageCard.dataset.state = data.state;
  byId("roomCode").textContent = data.room_code;
  byId("enrolledMetric").textContent = data.enrolled;
  byId("connectedMetric").textContent = data.connected;
  byId("lobbyConnectedCount").textContent = data.connected;
  byId("answersMetric").textContent = data.answers_received;
  byId("roomStatus").textContent = data.status === "open"
    ? "Sala abierta"
    : (data.status === "closed" ? "Partida finalizada" : "Partida en curso");

  const showLobby = data.state === "lobby_open" && data.status !== "closed";
  byId("roomPanel").classList.toggle("hidden", !showLobby);
  byId("hostLayout").classList.toggle("game-in-progress", !showLobby);
  byId("hostLayout").classList.toggle("lobby-layout", showLobby);
  byId("metricGrid").classList.add("hidden");
  stageCard.classList.toggle("hidden", showLobby);
  byId("participantsCard").classList.toggle("hidden", !showLobby);
  byId("participantsCard").classList.toggle("lobby-focus", showLobby);
  renderParticipants(data.participants || []);

  const content = byId("stageContent");
  content.className = "stage-content";
  content.replaceChildren();
  byId("stageControls").replaceChildren();

  if (data.status === "closed") renderClosed(content);
  else if (showLobby) renderLobby(data);
  else if (data.state === "qualifier_open") renderQualifier(content, data);
  else if (data.state === "qualifier_results") renderQualifierResults(content, data);
  else if (data.state === "player_selection") renderSelection(content, data);
  else if (data.state === "round_intro") renderRoundIntro(content, data);
  else if (["question_active", "lifeline_active", "answer_revealed"].includes(data.state)) {
    renderRegularQuestion(content, data);
  } else if (data.state === "round_summary") renderRoundSummary(content, data);
  else if (data.state === "session_summary") renderSessionSummary(content, data);
  else {
    const scene = node("section", "v3-scene");
    const card = node("div", "v3-scene-card");
    card.append(node("h1", "scene-title", "PREPARANDO EXPERIENCIA"));
    card.append(node("p", "scene-support-copy", "Espera un momento."));
    scene.append(card);
    content.append(scene);
  }
  syncAudio(data);
}

async function refresh() {
  try {
    render(await api(`/api/games/${code}`));
    byId("hostError").textContent = "";
  } catch (error) {
    if (error.message !== "Sesión finalizada") byId("hostError").textContent = error.message;
  }
}

async function perform(path, body = null) {
  if (busy) return;
  busy = true;
  byId("hostError").textContent = "";
  try {
    await api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });
    await refresh();
  } catch (error) {
    byId("hostError").textContent = error.message;
  } finally {
    busy = false;
    if (snapshot?.state === "lobby_open") renderLobby(snapshot);
  }
}

byId("roomCode").textContent = code;
byId("roomQr").src = `/api/rooms/${code}/qr`;
byId("lobbyStartButton").addEventListener("click", () => {
  gameAudio.enable("intro");
  perform(`/api/games/${code}/qualifier/start`);
});
byId("logoutButton").addEventListener("click", async () => {
  gameAudio.stopMusic();
  await fetch("/api/auth/logout", { method: "POST" });
  location.replace("/admin");
});
byId("fullscreenButton").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    byId("roomMessage").textContent = "La pantalla completa no está disponible en este navegador.";
  }
});
document.addEventListener("fullscreenchange", () => {
  byId("fullscreenButton").textContent = document.fullscreenElement ? "Salir de pantalla completa" : "Pantalla completa";
});

refresh();
setInterval(refresh, 750);
