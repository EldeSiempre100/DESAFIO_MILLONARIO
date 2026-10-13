(function () {
  "use strict";

  const selectorButtons = Array.from(document.querySelectorAll(".question-count-option"));
  const help = byId("questionCountHelp");
  const originalRenderLobby = renderLobby;
  const originalRenderRoundIntro = renderRoundIntro;

  function selectedQuestionCount(data) {
    const configured = Number(data.settings?.questions_per_round || 5);
    return [1, 3, 5].includes(configured) ? configured : 5;
  }

  function updateSelector(data) {
    const selected = selectedQuestionCount(data);
    selectorButtons.forEach((button) => {
      const value = Number(button.dataset.questions);
      const isSelected = value === selected;
      button.classList.toggle("selected", isSelected);
      button.setAttribute("aria-pressed", String(isSelected));
      button.disabled = busy || data?.state !== "lobby_open";
    });
    if (help) {
      help.textContent = selected === 1
        ? "Modo seleccionado: 1 pregunta por jugador."
        : `Modo seleccionado: ${selected} preguntas por jugador.`;
    }
  }

  function phase6RenderLobby(data) {
    originalRenderLobby(data);
    updateSelector(data);
  }

  function phase6RenderRoundIntro(content, data) {
    originalRenderRoundIntro(content, data);
    const total = Number(data?.round?.question_total || 5);
    const copies = content.querySelectorAll(".round-intro-copy");
    if (copies.length >= 2) {
      copies[1].textContent = total === 1
        ? "1 uso máximo de cada comodín en esta ronda"
        : "3 usos de cada comodín disponibles";
    }
  }

  renderLobby = phase6RenderLobby;
  renderRoundIntro = phase6RenderRoundIntro;

  selectorButtons.forEach((button) => {
    button.disabled = false;
    button.removeAttribute("title");
    button.addEventListener("click", () => {
      if (busy || snapshot?.state !== "lobby_open") return;
      const questionsPerRound = Number(button.dataset.questions);
      if (![1, 3, 5].includes(questionsPerRound)) return;
      perform(`/api/games/${code}/settings`, {
        questions_per_round: questionsPerRound,
      });
    });
  });

  if (snapshot?.state === "lobby_open") updateSelector(snapshot);
}());
