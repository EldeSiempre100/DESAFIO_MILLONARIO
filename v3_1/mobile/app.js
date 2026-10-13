"use strict";

let roomCode = "";
const apiBase = "/api/v1";
const storageKey = "millonario-v3:active-room";
let avatarCatalog = [
  {id: "explorer", symbol: "🤠", label: "Explorador"},
  {id: "strategist", symbol: "🤓", label: "Estratega"},
  {id: "creative", symbol: "😎", label: "Creativo"},
  {id: "curious", symbol: "🧐", label: "Curioso"},
  {id: "scientist", symbol: "😄", label: "Optimista"},
  {id: "digital", symbol: "🙂", label: "Sereno"},
  {id: "adventurer", symbol: "🥳", label: "Entusiasta"},
  {id: "star", symbol: "🤩", label: "Estrella"},
];

const ui = {
  join: document.querySelector("#joinView"),
  status: document.querySelector("#statusView"),
  answer: document.querySelector("#answerView"),
  closed: document.querySelector("#closedView"),
  roomCode: document.querySelector("#roomCode"),
  joinForm: document.querySelector("#joinForm"),
  alias: document.querySelector("#alias"),
  joinError: document.querySelector("#joinError"),
  avatarGrid: document.querySelector("#avatarGrid"),
  network: document.querySelector("#networkDot"),
  myAvatar: document.querySelector("#myAvatar"),
  myAlias: document.querySelector("#myAlias"),
  statusBadge: document.querySelector("#statusBadge"),
  statusTitle: document.querySelector("#statusTitle"),
  statusMessage: document.querySelector("#statusMessage"),
  roomSummary: document.querySelector("#roomSummary"),
  answerMode: document.querySelector("#answerMode"),
  answerStatus: document.querySelector("#answerStatus"),
  timerBar: document.querySelector("#timerBar"),
  closedTitle: document.querySelector("#closedTitle"),
  closedMessage: document.querySelector("#closedMessage"),
  chosenAnswer: document.querySelector("#chosenAnswer"),
  answerButtons: [...document.querySelectorAll("[data-answer]")],
};

const state = {
  participantId: "",
  alias: "",
  avatar: "explorer",
  avatarSymbol: "🤠",
  token: "",
  deviceId: "",
  role: "audience",
  opening: null,
  websocket: null,
  reconnectAttempt: 0,
  heartbeatTimer: null,
  timerAnimation: null,
  answered: false,
  intentionallyClosed: false,
};

function createDeviceId() {
  const webCrypto = globalThis.crypto;
  if (typeof webCrypto?.randomUUID === "function") {
    try {
      return webCrypto.randomUUID();
    } catch {
      // Algunos navegadores exponen la función, pero la bloquean sobre HTTP local.
    }
  }
  if (typeof webCrypto?.getRandomValues === "function") {
    try {
      const bytes = new Uint8Array(16);
      webCrypto.getRandomValues(bytes);
      bytes[6] = (bytes[6] & 0x0f) | 0x40;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      const hex = [...bytes].map(value => value.toString(16).padStart(2, "0"));
      return [
        hex.slice(0, 4).join(""),
        hex.slice(4, 6).join(""),
        hex.slice(6, 8).join(""),
        hex.slice(8, 10).join(""),
        hex.slice(10, 16).join(""),
      ].join("-");
    } catch {
      // Se conserva un último mecanismo compatible con navegadores antiguos.
    }
  }
  return `device-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
}

function loadIdentity() {
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || "{}");
    state.participantId = stored.participantId || "";
    state.alias = stored.alias || "";
    state.avatar = stored.avatar || "explorer";
    state.token = stored.token || "";
    if (stored.roomCode && stored.roomCode !== roomCode) {
      state.participantId = "";
      state.alias = "";
      state.avatar = "explorer";
      state.token = "";
      state.deviceId = createDeviceId();
    } else {
      state.deviceId = stored.deviceId || createDeviceId();
    }
  } catch {
    state.deviceId = createDeviceId();
  }
  if (!state.deviceId) state.deviceId = createDeviceId();
}

function saveIdentity() {
  localStorage.setItem(storageKey, JSON.stringify({
    participantId: state.participantId,
    alias: state.alias,
    avatar: state.avatar,
    token: state.token,
    deviceId: state.deviceId,
    roomCode,
  }));
}

function selectedAvatar() {
  return avatarCatalog.find(item => item.id === state.avatar) || avatarCatalog[0];
}

function chooseAvatar(avatarId) {
  const avatar = avatarCatalog.find(item => item.id === avatarId) || avatarCatalog[0];
  state.avatar = avatar.id;
  state.avatarSymbol = avatar.symbol;
  [...ui.avatarGrid.querySelectorAll("[data-avatar]")].forEach(button => {
    button.setAttribute("aria-checked", String(button.dataset.avatar === avatar.id));
  });
}

function renderAvatars(items) {
  if (Array.isArray(items) && items.length) avatarCatalog = items;
  ui.avatarGrid.replaceChildren();
  avatarCatalog.forEach(avatar => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "avatar-option";
    button.dataset.avatar = avatar.id;
    button.setAttribute("role", "radio");
    button.setAttribute("aria-label", avatar.label);
    const symbol = document.createElement("span");
    symbol.className = "avatar-option__symbol";
    symbol.textContent = avatar.symbol;
    const label = document.createElement("span");
    label.className = "avatar-option__label";
    label.textContent = avatar.label;
    button.append(symbol, label);
    button.addEventListener("click", () => chooseAvatar(avatar.id));
    ui.avatarGrid.append(button);
  });
  chooseAvatar(state.avatar);
}

function show(view) {
  [ui.join, ui.status, ui.answer, ui.closed].forEach(item => item.classList.add("hidden"));
  view.classList.remove("hidden");
}

function setOnline(online) {
  ui.network.classList.toggle("network--online", online);
  ui.network.classList.toggle("network--offline", !online);
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || {};
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? "Los datos de ingreso no son válidos. Recarga la página e inténtalo nuevamente."
        : detail.message;
    throw new Error(message || "No fue posible comunicarse con la sala.");
  }
  return payload;
}

async function bootstrap() {
  try {
    const room = await request("/bootstrap");
    roomCode = room.room_code || "";
    ui.roomCode.textContent = roomCode || "----";
    loadIdentity();
    renderAvatars(room.avatars);
    setOnline(true);
  } catch (error) {
    ui.joinError.textContent = error.message;
    setOnline(false);
    return;
  }
  if (state.token) {
    try {
      const participant = await request("/reconnect", {
        method: "POST",
        body: JSON.stringify({token: state.token}),
      });
      state.participantId = participant.participant_id;
      state.alias = participant.alias;
      state.avatar = participant.avatar || state.avatar;
      state.avatarSymbol = participant.avatar_symbol || selectedAvatar().symbol;
      state.role = participant.role;
      enterWaiting();
      connectWebSocket();
      return;
    } catch {
      state.participantId = "";
      state.token = "";
      state.deviceId = createDeviceId();
      saveIdentity();
    }
  }
  show(ui.join);
}

ui.joinForm.addEventListener("submit", async event => {
  event.preventDefault();
  ui.joinError.textContent = "";
  const submit = ui.joinForm.querySelector("button");
  submit.disabled = true;
  try {
    const participant = await request("/join", {
      method: "POST",
      body: JSON.stringify({
        alias: ui.alias.value,
        avatar: state.avatar,
        device_id: state.deviceId,
        client_version: "3.1.4",
      }),
    });
    state.participantId = participant.participant_id;
    state.alias = participant.alias;
    state.avatar = participant.avatar || state.avatar;
    state.avatarSymbol = participant.avatar_symbol || selectedAvatar().symbol;
    state.token = participant.token;
    state.role = participant.role;
    saveIdentity();
    enterWaiting();
    connectWebSocket();
  } catch (error) {
    ui.joinError.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

function enterWaiting(title = "Estás dentro", message = "Mira la pantalla principal y espera las instrucciones.") {
  state.opening = null;
  state.answered = false;
  ui.myAlias.textContent = state.alias;
  ui.myAvatar.textContent = state.avatarSymbol || selectedAvatar().symbol;
  ui.statusTitle.textContent = title;
  ui.statusMessage.textContent = message;
  ui.statusBadge.textContent = state.role === "selected" ? "Participante" : "Conectado";
  show(ui.status);
}

function wsUrl() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}/ws/v1/room?token=${encodeURIComponent(state.token)}`;
}

function connectWebSocket() {
  clearInterval(state.heartbeatTimer);
  if (!state.token) return;
  if (
    state.websocket
    && [WebSocket.OPEN, WebSocket.CONNECTING].includes(state.websocket.readyState)
  ) {
    return;
  }
  const socket = new WebSocket(wsUrl());
  state.websocket = socket;
  socket.addEventListener("open", () => {
    state.reconnectAttempt = 0;
    setOnline(true);
    state.heartbeatTimer = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({type: "heartbeat"}));
      }
    }, 10000);
  });
  socket.addEventListener("message", event => {
    try { handleEvent(JSON.parse(event.data)); } catch { /* mensaje inválido */ }
  });
  socket.addEventListener("close", () => {
    clearInterval(state.heartbeatTimer);
    setOnline(false);
    if (!state.intentionallyClosed) {
      const wait = Math.min(12000, 600 * (2 ** state.reconnectAttempt++));
      setTimeout(connectWebSocket, wait);
    }
  });
  socket.addEventListener("error", () => {
    if (socket.readyState !== WebSocket.CLOSED) socket.close();
  });
}

function handleEvent(event) {
  const payload = event.payload || {};
  switch (event.type) {
    case "room.snapshot":
      if (payload.me) {
        state.role = payload.me.role || state.role;
        state.avatar = payload.me.avatar || state.avatar;
        state.avatarSymbol = payload.me.avatar_symbol || selectedAvatar().symbol;
        ui.myAvatar.textContent = state.avatarSymbol;
        ui.statusBadge.textContent = state.role === "selected" ? "Participante" : "Conectado";
      }
      ui.roomSummary.textContent = `${payload.enrolled || 0} de ${payload.capacity || 30} personas enroladas`;
      if (payload.opening && !state.answered) {
        openAnswers(payload.opening);
      } else if (!payload.opening) {
        if (state.role === "selected") {
          enterWaiting(
            "Participante seleccionado",
            "Sigue las instrucciones del anfitrión en la pantalla principal.",
          );
        } else if (payload.status === "locked") {
          enterWaiting(
            "Sigues participando",
            "Espera la próxima votación o el comodín Consulta con el público.",
          );
        } else {
          enterWaiting();
        }
      }
      break;
    case "room.locked":
      enterWaiting(
        "Clasificación iniciando",
        "Las alternativas se activarán automáticamente.",
      );
      break;
    case "qualifier.opened":
      openAnswers(payload, "Pregunta clasificatoria");
      break;
    case "audience.opened":
      openAnswers(payload, "Consulta con el público");
      break;
    case "answer.ack":
      handleAnswerAck(payload);
      break;
    case "qualifier.closed":
      enterWaiting(
        "Clasificación finalizada",
        "Espera la selección. Si no eres elegido, continuarás disponible como público.",
      );
      break;
    case "audience.closed":
      enterWaiting(
        "Consulta finalizada",
        "La respuesta quedó registrada. Continúa atento a la pantalla principal.",
      );
      break;
    case "candidates.selected":
      state.role = (payload.participant_ids || []).includes(state.participantId)
        ? "selected" : "audience";
      if (state.role === "selected") {
        enterWaiting("¡Fuiste seleccionado!", "Acércate al anfitrión para comenzar tu ronda.");
      } else {
        enterWaiting("Sigues participando", "Podrás responder cuando se active Consulta con el público.");
      }
      break;
    case "round.started":
      if (payload.participant_id === state.participantId) {
        enterWaiting("Tu ronda está activa", "Responde verbalmente al anfitrión. Tu pulsador queda reservado.");
      } else {
        enterWaiting("Ronda en curso", `${payload.alias || "Un participante"} está jugando. Espera un comodín del público.`);
      }
      break;
    case "client.waiting":
      enterWaiting(payload.title || "Espera", payload.message || "");
      break;
    case "session.finished":
      state.intentionallyClosed = payload.reason === "host_closed";
      enterWaiting(
        "Experiencia finalizada",
        payload.reason === "host_closed"
          ? "La sala fue cerrada por el anfitrión."
          : "Gracias por participar. El anfitrión puede iniciar una nueva partida.",
      );
      break;
    case "session.restarted":
      state.intentionallyClosed = false;
      state.role = "audience";
      state.opening = null;
      state.answered = false;
      enterWaiting(
        "Nueva partida",
        "Sigues enrolado y volverás a participar en la clasificación.",
      );
      break;
    case "error":
      ui.answerStatus.textContent = payload.message || "Ocurrió un error recuperable.";
      break;
  }
}

function openAnswers(opening, label) {
  state.opening = opening;
  state.answered = false;
  ui.answerMode.textContent = label || (opening.type === "audience" ? "Consulta con el público" : "Pregunta clasificatoria");
  ui.answerStatus.textContent = "Esperando tu respuesta";
  ui.answerButtons.forEach(button => {
    button.disabled = false;
    button.classList.remove("answer--selected");
  });
  show(ui.answer);
  startTimer(opening.duration_ms || 15000);
}

function startTimer(duration) {
  cancelAnimationFrame(state.timerAnimation);
  const start = performance.now();
  const frame = now => {
    const remaining = Math.max(0, 1 - ((now - start) / duration));
    ui.timerBar.style.transform = `scaleX(${remaining})`;
    if (remaining > 0 && state.opening) state.timerAnimation = requestAnimationFrame(frame);
  };
  state.timerAnimation = requestAnimationFrame(frame);
}

ui.answerButtons.forEach(button => {
  button.addEventListener("click", () => {
    if (!state.opening || state.answered || state.websocket?.readyState !== WebSocket.OPEN) return;
    state.answered = true;
    const alternative = button.dataset.answer;
    ui.answerButtons.forEach(item => item.disabled = true);
    button.classList.add("answer--selected");
    ui.answerStatus.textContent = "Enviando respuesta…";
    state.websocket.send(JSON.stringify({
      type: "answer.submit",
      opening_id: state.opening.opening_id,
      alternative,
    }));
  });
});

function handleAnswerAck(payload) {
  if (["accepted", "duplicate"].includes(payload.status)) {
    cancelAnimationFrame(state.timerAnimation);
    ui.chosenAnswer.textContent = payload.alternative || "";
    ui.closedTitle.textContent = payload.status === "accepted"
      ? "Respuesta recibida" : "Respuesta ya registrada";
    ui.closedMessage.textContent = payload.message || "Espera el resultado en la pantalla principal.";
    show(ui.closed);
  } else {
    state.answered = false;
    ui.answerButtons.forEach(button => button.disabled = true);
    ui.answerStatus.textContent = payload.message || "La votación ya cerró.";
  }
}

window.addEventListener("beforeunload", () => {
  state.intentionallyClosed = true;
});

window.addEventListener("online", () => {
  state.intentionallyClosed = false;
  connectWebSocket();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !state.token) return;
  state.intentionallyClosed = false;
  connectWebSocket();
});

bootstrap();
