const code = location.pathname.split("/").filter(Boolean).pop();
const letters = ["A", "B", "C", "D"];
const tokenKey = `desafio:room:${code}:token`;
const deviceKey = "desafio:device";
let token = localStorage.getItem(tokenKey);
let selectedAvatar = "explorer";
let socket = null;
let currentOpening = null;
let heartbeatTimer = null;
let timerFrame = null;
let reconnectDelay = 800;
let shouldReconnect = true;
let selectedAlternative = null;

const byId = (id) => document.getElementById(id);
const deviceId = localStorage.getItem(deviceKey) || (crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`);
localStorage.setItem(deviceKey, deviceId);
// Limpieza de una preferencia obsoleta de V4 previa a Fase 5. El pulsador ya no reproduce audio.
localStorage.removeItem("desafio:player-sound");
byId("roomCode").textContent = code;

function detailMessage(payload, fallback) {
  const detail = payload?.detail;
  return detail?.message || (typeof detail === "string" ? detail : fallback);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(detailMessage(payload, "No fue posible completar la acción."));
  return payload;
}

function setNetwork(online, label = online ? "Conectado" : "Reconectando") {
  byId("networkIndicator").classList.toggle("online", online);
  byId("networkIndicator").textContent = label;
}

function showIdentity(participant, gameRole = "audience", active = false) {
  byId("identityAvatar").textContent = participant.avatar_symbol || "🙂";
  byId("identityAlias").textContent = participant.alias;
  byId("identityRole").textContent = active
    ? "Jugador activo"
    : (gameRole === "player" ? "Jugador seleccionado" : "Público");
  byId("joinView").classList.add("hidden");
  byId("playerRoomCode").classList.add("hidden");
  byId("gameView").classList.remove("hidden");
}

function renderAvatars(avatars) {
  const grid = byId("avatarGrid");
  grid.replaceChildren();
  avatars.forEach((avatar, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `avatar-button${index === 0 ? " selected" : ""}`;
    button.textContent = avatar.symbol;
    button.title = avatar.label;
    button.setAttribute("aria-label", avatar.label);
    button.addEventListener("click", () => {
      selectedAvatar = avatar.id;
      grid.querySelectorAll("button").forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
    });
    grid.append(button);
  });
  selectedAvatar = avatars[0]?.id || "explorer";
}

function showWaiting(title, message) {
  cancelAnimationFrame(timerFrame);
  currentOpening = null;
  selectedAlternative = null;
  byId("questionView").classList.add("hidden");
  byId("waitingView").classList.remove("hidden");
  byId("waitingTitle").textContent = title || "Estás dentro";
  byId("waitingMessage").textContent = message || "Mira la pantalla principal y espera las instrucciones.";
}

function startTimer(opening) {
  cancelAnimationFrame(timerFrame);
  const openedAt = Date.parse(opening.opened_at);
  const duration = Number(opening.duration_ms);
  const fill = byId("timerFill");
  const tick = () => {
    const remaining = Math.max(0, 1 - ((Date.now() - openedAt) / duration));
    byId("timerValue").textContent = String(Math.ceil((remaining * duration) / 1000));
    fill.style.transform = `scaleX(${remaining})`;
    if (remaining > 0 && currentOpening?.opening_id === opening.opening_id) {
      timerFrame = requestAnimationFrame(tick);
    } else if (currentOpening?.opening_id === opening.opening_id) {
      document.querySelectorAll(".answer-button").forEach((item) => { item.disabled = true; });
      if (byId("answerStatus").textContent === "Elige una alternativa.") {
        byId("answerStatus").textContent = "Tiempo finalizado.";
      }
    }
  };
  tick();
}

function showQuestion(question) {
  const opening = question.opening;
  const allowedAnswers = new Set(opening.allowed_answers || letters);
  const isNewOpening = currentOpening?.opening_id !== opening.opening_id;
  currentOpening = opening;
  if (isNewOpening) selectedAlternative = null;

  byId("waitingView").classList.add("hidden");
  byId("questionView").classList.remove("hidden");
  byId("answerStatus").textContent = question.answered ? "Respuesta recibida." : "Elige una alternativa.";

  const grid = byId("answerGrid");
  grid.replaceChildren();
  letters.filter((letter) => allowedAnswers.has(letter)).forEach((letter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `answer-button${selectedAlternative === letter ? " selected" : ""}`;
    button.disabled = Boolean(question.answered);
    button.setAttribute("aria-label", `Alternativa ${letter}`);
    const key = document.createElement("span");
    key.className = "answer-key";
    key.textContent = letter;
    button.append(key);
    button.addEventListener("click", () => submitAnswer(letter, button));
    grid.append(button);
  });
  startTimer(opening);
}

function submitAnswer(alternative, button) {
  if (!currentOpening || socket?.readyState !== WebSocket.OPEN) return;
  document.querySelectorAll(".answer-button").forEach((item) => { item.disabled = true; });
  button.classList.add("selected");
  selectedAlternative = alternative;
  byId("answerStatus").textContent = "Enviando respuesta…";
  socket.send(JSON.stringify({
    type: "answer.submit",
    opening_id: currentOpening.opening_id,
    alternative,
  }));
}

function handleEvent(message) {
  const payload = message.payload || {};
  if (message.type === "room.snapshot") {
    showIdentity(payload.me, payload.game_role, payload.is_active_player);
    if (payload.question) showQuestion(payload.question);
    else showWaiting(payload.waiting?.title, payload.waiting?.message);
  } else if (message.type === "answer.ack") {
    const messages = {
      accepted: "Respuesta recibida.",
      duplicate: "Tu primera respuesta ya está registrada.",
      late: "La respuesta llegó después del cierre.",
      forbidden: "Este pulsador no está habilitado en este momento.",
      invalid: "La alternativa no es válida.",
    };
    byId("answerStatus").textContent = messages[payload.status] || payload.message || "La respuesta no pudo registrarse.";
  } else if (message.type === "error") {
    byId("answerStatus").textContent = payload.message || "Ocurrió un problema.";
  }
}

function connect() {
  if (!token || !shouldReconnect) return;
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  socket = new WebSocket(`${protocol}//${location.host}/ws/rooms/${code}?token=${encodeURIComponent(token)}`);
  setNetwork(false, "Conectando");
  socket.addEventListener("open", () => {
    reconnectDelay = 800;
    setNetwork(true);
    clearInterval(heartbeatTimer);
    heartbeatTimer = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "heartbeat" }));
    }, 20000);
  });
  socket.addEventListener("message", (event) => {
    try { handleEvent(JSON.parse(event.data)); } catch { setNetwork(false); }
  });
  socket.addEventListener("close", (event) => {
    clearInterval(heartbeatTimer);
    setNetwork(false, shouldReconnect ? "Reconectando" : "Finalizado");
    if (event.code === 4401) {
      token = null;
      localStorage.removeItem(tokenKey);
      location.reload();
      return;
    }
    if (shouldReconnect) {
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.7, 10000);
    }
  });
}

async function initialize() {
  try {
    const room = await api(`/api/rooms/${code}/bootstrap`);
    byId("roomAvailability").textContent = room.status === "open"
      ? `${room.enrolled} de ${room.capacity} participantes en la sala.`
      : "La sala ya inició.";
    if (token) {
      try {
        const participant = await api(`/api/rooms/${code}/reconnect`, {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        showIdentity(participant, participant.role === "selected" ? "player" : "audience");
        connect();
        return;
      } catch {
        token = null;
        localStorage.removeItem(tokenKey);
      }
    }
    if (room.status !== "open") {
      byId("joinError").textContent = "La partida ya comenzó y no admite nuevos ingresos.";
      return;
    }
    renderAvatars(room.avatars);
    byId("joinForm").classList.remove("hidden");
  } catch (error) {
    byId("roomAvailability").textContent = "Sala no disponible.";
    byId("joinError").textContent = error.message;
  }
}

byId("joinForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  byId("joinButton").disabled = true;
  byId("joinError").textContent = "";
  try {
    const participant = await api(`/api/rooms/${code}/join`, {
      method: "POST",
      body: JSON.stringify({
        alias: byId("alias").value.trim(),
        device_id: deviceId,
        avatar: selectedAvatar,
      }),
    });
    token = participant.token;
    localStorage.setItem(tokenKey, token);
    showIdentity(participant);
    connect();
  } catch (error) {
    byId("joinError").textContent = error.message;
    byId("joinButton").disabled = false;
  }
});

initialize();
