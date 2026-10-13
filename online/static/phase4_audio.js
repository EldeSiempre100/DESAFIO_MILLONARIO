(function () {
  "use strict";

  const AMBIENT_STATES = new Set([
    "lobby_open",
    "qualifier_open",
    "qualifier_results",
    "player_selection",
    "round_intro",
    "round_summary",
    "session_summary",
  ]);

  const AMBIENT_EVENTS = new Set([
    "lobby_opened",
    "qualifier_started",
    "qualifier_finished",
    "player_selection_started",
    "players_confirmed",
    "round_finished",
    "round_intro",
    "session_finished",
    "session_restarted",
  ]);

  const QUESTION_CUE_FALLBACK_MS = 11650;

  function canonicalBackgroundForState(state) {
    if (AMBIENT_STATES.has(state)) return "intro";
    if (state === "question_active" || state === "lifeline_active") return "question";
    return null;
  }

  function canonicalRenderLifelines(parent, data) {
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
        // La acción sólo desbloquea audio. El evento autoritativo del servidor
        // decide qué cue corresponde; no adelantamos question_music aquí.
        gameAudio.enable(null);
        perform(`/api/games/${code}/lifelines/${name}`);
      });
      stack.append(button);
    });
    parent.append(stack);
  }

  function canonicalSyncAudio(data) {
    if (!gameAudio.enabled) return;

    const storageKey = `desafio:host:last-audio-event:${code}`;
    const eventId = Number(data.last_event?.id || 0);
    const previousId = Number(sessionStorage.getItem(storageKey) || 0);
    let startedQuestionSequence = false;

    if (eventId > previousId) {
      const name = data.last_event.name;

      if (name === "question_started") {
        // Ritmo recuperado del PPT histórico: cue de entrada (~11,49 s)
        // y luego música sostenida de pregunta.
        gameAudio.beginQuestionSequence({
          cue: "transition",
          music: "question",
          fallbackMs: QUESTION_CUE_FALLBACK_MS,
        });
        startedQuestionSequence = true;
      } else if (name === "answer_revealed") {
        gameAudio.cancelQuestionSequence();
        gameAudio.stopVoice();
        gameAudio.stopMusic({ fadeMs: 180 });
        gameAudio.play(data.last_event.correct ? "correct" : "incorrect");
      } else if (name === "lifeline_fifty") {
        // 50:50: efecto superpuesto; la tensión de pregunta continúa.
        gameAudio.play("lifeline");
      } else if (name === "lifeline_started") {
        // V3 usa canales separados: el timer queda pausado por servidor, pero
        // question_music continúa y llamada/público se superponen como voz.
        gameAudio.play("lifeline");
        gameAudio.playVoice(data.last_event.lifeline === "phone" ? "call" : "audience");
      } else if (name === "lifeline_finished") {
        gameAudio.stopVoice();
        // Si hubo recarga o alguna interrupción técnica, asegurar que la cama
        // de tensión de la misma pregunta siga activa sin repetir transition.
        if (!gameAudio.isQuestionSequenceActive() && gameAudio.musicName !== "question") {
          gameAudio.startMusic("question");
        }
      } else if (AMBIENT_EVENTS.has(name)) {
        gameAudio.cancelQuestionSequence();
        gameAudio.stopVoice();
        gameAudio.startMusic("intro");
      } else if (name === "game_finished") {
        gameAudio.cancelQuestionSequence();
        gameAudio.stopVoice();
        gameAudio.stopMusic({ fadeMs: 180 });
      }

      sessionStorage.setItem(storageKey, String(eventId));
    }

    // Reconciliación idempotente para polling, reconexión o recarga del host.
    // Nunca debe saltarse el cue recién iniciado por question_started.
    if (data.status === "closed") {
      gameAudio.cancelQuestionSequence();
      gameAudio.stopVoice();
      gameAudio.stopMusic({ fadeMs: 180 });
      return;
    }

    if (AMBIENT_STATES.has(data.state)) {
      gameAudio.cancelQuestionSequence();
      gameAudio.stopVoice();
      gameAudio.startMusic("intro");
      return;
    }

    if (data.state === "question_active" || data.state === "lifeline_active") {
      if (
        !startedQuestionSequence
        && !gameAudio.isQuestionSequenceActive()
        && gameAudio.musicName !== "question"
      ) {
        // Si el host recarga a mitad de una pregunta/comodín, retoma la tensión
        // sin volver a representar una entrada que ya ocurrió.
        gameAudio.startMusic("question");
      }
      return;
    }

    if (data.state === "answer_revealed") return;

    gameAudio.cancelQuestionSequence();
    gameAudio.stopVoice();
    gameAudio.stopMusic({ fadeMs: 180 });
  }

  // host.js es un script clásico; sus declaraciones globales son bindings
  // mutables compartidos con este script diferido. La Fase 4 reemplaza sólo la
  // política audiovisual y deja intacta la máquina de estados y el render.
  backgroundForState = canonicalBackgroundForState;
  renderLifelines = canonicalRenderLifelines;
  syncAudio = canonicalSyncAudio;

  gameAudio.preloadSources();
  window.__desafioPhase4Audio = Object.freeze({
    questionCueFallbackMs: QUESTION_CUE_FALLBACK_MS,
    ambientStates: [...AMBIENT_STATES],
  });

  // Reconciliar una carga inicial que haya terminado antes de instalar la
  // política canónica. No muta estado del servidor.
  if (snapshot) syncAudio(snapshot);
}());
