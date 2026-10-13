(function attachQuestionEditorLogic(root, factory) {
  const logic = factory();
  if (typeof module === "object" && module.exports) module.exports = logic;
  root.Phase7QuestionEditor = logic;
})(typeof globalThis !== "undefined" ? globalThis : window, function createQuestionEditorLogic() {
  const LETTERS = ["A", "B", "C", "D"];
  const REQUIRED_COUNT = 12;
  const PROMPT_LIMIT = 320;
  const ANSWER_LIMIT = 140;

  function blankQuestion() {
    return {
      prompt: "",
      answers: ["", "", "", ""],
      correct_index: 0,
    };
  }

  function cloneQuestion(question) {
    return {
      prompt: String(question?.prompt || ""),
      answers: LETTERS.map((_, index) => String(question?.answers?.[index] || "")),
      correct_index: Number.isInteger(question?.correct_index) ? question.correct_index : 0,
    };
  }

  function cloneDraft(snapshot) {
    return {
      title: String(snapshot?.title || "Preguntas del desafío"),
      questions: (snapshot?.questions || []).map(cloneQuestion),
    };
  }

  function clampIndex(index, length) {
    if (!length) return 0;
    return Math.max(0, Math.min(Number(index) || 0, length - 1));
  }

  function addQuestion(draft, afterIndex = draft.questions.length - 1) {
    const next = cloneDraft(draft);
    const insertAt = Math.max(0, Math.min(Number(afterIndex) + 1, next.questions.length));
    next.questions.splice(insertAt, 0, blankQuestion());
    return { draft: next, selectedIndex: insertAt };
  }

  function duplicateQuestion(draft, index) {
    const next = cloneDraft(draft);
    if (!next.questions.length) return addQuestion(next, -1);
    const sourceIndex = clampIndex(index, next.questions.length);
    next.questions.splice(sourceIndex + 1, 0, cloneQuestion(next.questions[sourceIndex]));
    return { draft: next, selectedIndex: sourceIndex + 1 };
  }

  function moveQuestion(draft, index, direction) {
    const next = cloneDraft(draft);
    const from = clampIndex(index, next.questions.length);
    const to = from + Number(direction || 0);
    if (to < 0 || to >= next.questions.length || from === to) {
      return { draft: next, selectedIndex: from };
    }
    const [item] = next.questions.splice(from, 1);
    next.questions.splice(to, 0, item);
    return { draft: next, selectedIndex: to };
  }

  function deleteQuestion(draft, index) {
    const next = cloneDraft(draft);
    if (!next.questions.length) return { draft: next, selectedIndex: 0 };
    const removedAt = clampIndex(index, next.questions.length);
    next.questions.splice(removedAt, 1);
    return { draft: next, selectedIndex: clampIndex(removedAt, next.questions.length) };
  }

  function updateQuestion(draft, index, patch) {
    const next = cloneDraft(draft);
    if (!next.questions.length) next.questions.push(blankQuestion());
    const selected = clampIndex(index, next.questions.length);
    const question = cloneQuestion(next.questions[selected]);
    if (Object.prototype.hasOwnProperty.call(patch, "prompt")) {
      question.prompt = String(patch.prompt).slice(0, PROMPT_LIMIT);
    }
    if (Object.prototype.hasOwnProperty.call(patch, "correct_index")) {
      const correct = Number(patch.correct_index);
      question.correct_index = correct >= 0 && correct <= 3 ? correct : 0;
    }
    if (patch.answers) {
      question.answers = LETTERS.map((_, answerIndex) => {
        const value = Object.prototype.hasOwnProperty.call(patch.answers, answerIndex)
          ? patch.answers[answerIndex]
          : question.answers[answerIndex];
        return String(value || "").slice(0, ANSWER_LIMIT);
      });
    }
    next.questions[selected] = question;
    return next;
  }

  function serializeForPut(draft, expectedRevision) {
    return {
      title: String(draft.title || "Preguntas del desafío"),
      questions: draft.questions.map(cloneQuestion),
      expected_revision: String(expectedRevision || ""),
    };
  }

  function normalized(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
  }

  function validateQuestion(question) {
    const errors = [];
    if (!String(question.prompt || "").trim()) errors.push("El enunciado es obligatorio.");
    if (String(question.prompt || "").length > PROMPT_LIMIT) errors.push("El enunciado supera 320 caracteres.");
    if (!Array.isArray(question.answers) || question.answers.length !== 4) {
      errors.push("Cada pregunta debe tener cuatro alternativas.");
    } else {
      question.answers.forEach((answer, index) => {
        if (!String(answer || "").trim()) errors.push(`La alternativa ${LETTERS[index]} es obligatoria.`);
        if (String(answer || "").length > ANSWER_LIMIT) {
          errors.push(`La alternativa ${LETTERS[index]} supera 140 caracteres.`);
        }
      });
      const unique = new Set(question.answers.map(normalized));
      if (unique.size !== 4) errors.push("Las cuatro alternativas deben ser diferentes.");
    }
    if (!Number.isInteger(question.correct_index) || question.correct_index < 0 || question.correct_index > 3) {
      errors.push("La respuesta correcta debe estar entre A y D.");
    }
    return errors;
  }

  function validateBank(draft) {
    const errors = [];
    if (draft.questions.length !== REQUIRED_COUNT) {
      errors.push("La versión web requiere exactamente 12 preguntas activas para conservar los modos 1 / 3 / 5.");
    }
    const prompts = draft.questions.map((question) => normalized(question.prompt)).filter(Boolean);
    if (new Set(prompts).size !== prompts.length) {
      errors.push("Hay enunciados duplicados.");
    }
    draft.questions.forEach((question, index) => {
      const questionErrors = validateQuestion(question);
      if (questionErrors.length) errors.push(`Pregunta ${index + 1}: ${questionErrors[0]}`);
    });
    return { valid: errors.length === 0, errors };
  }

  function isDirty(snapshot, draft) {
    if (!snapshot) return false;
    return JSON.stringify(cloneDraft(snapshot)) !== JSON.stringify(cloneDraft(draft));
  }

  return {
    LETTERS,
    REQUIRED_COUNT,
    PROMPT_LIMIT,
    ANSWER_LIMIT,
    blankQuestion,
    cloneDraft,
    cloneQuestion,
    addQuestion,
    duplicateQuestion,
    moveQuestion,
    deleteQuestion,
    updateQuestion,
    serializeForPut,
    validateQuestion,
    validateBank,
    isDirty,
  };
});
