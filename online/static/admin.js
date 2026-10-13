const loginView = document.querySelector("#loginView");
const dashboardView = document.querySelector("#dashboardView");
const loginForm = document.querySelector("#loginForm");
const loginError = document.querySelector("#loginError");
const dashboardError = document.querySelector("#dashboardError");
const createButton = document.querySelector("#createGameButton");
const editQuestionsButton = document.querySelector("#editQuestionsButton");
const editChoiceDialog = document.querySelector("#editChoiceDialog");
const closeEditChoiceButton = document.querySelector("#closeEditChoiceButton");
const manualEditorButton = document.querySelector("#manualEditorButton");
const importExcelButton = document.querySelector("#importExcelButton");
const logoutButton = document.querySelector("#logoutButton");

const manualEditorDialog = document.querySelector("#manualEditorDialog");
const editorLoading = document.querySelector("#editorLoading");
const editorWorkspace = document.querySelector("#editorWorkspace");
const editorServerMessage = document.querySelector("#editorServerMessage");
const editorValidationMessage = document.querySelector("#editorValidationMessage");
const editorWritableBadge = document.querySelector("#editorWritableBadge");
const editorDirtyBadge = document.querySelector("#editorDirtyBadge");
const questionCount = document.querySelector("#questionCount");
const questionListStatus = document.querySelector("#questionListStatus");
const questionList = document.querySelector("#questionList");
const questionPrompt = document.querySelector("#questionPrompt");
const promptCounter = document.querySelector("#promptCounter");
const answerInputs = [
  document.querySelector("#answerA"),
  document.querySelector("#answerB"),
  document.querySelector("#answerC"),
  document.querySelector("#answerD"),
];
const answerCounters = [
  document.querySelector("#answerCounterA"),
  document.querySelector("#answerCounterB"),
  document.querySelector("#answerCounterC"),
  document.querySelector("#answerCounterD"),
];
const correctAnswer = document.querySelector("#correctAnswer");
const newQuestionButton = document.querySelector("#newQuestionButton");
const duplicateQuestionButton = document.querySelector("#duplicateQuestionButton");
const moveQuestionUpButton = document.querySelector("#moveQuestionUpButton");
const moveQuestionDownButton = document.querySelector("#moveQuestionDownButton");
const deleteQuestionButton = document.querySelector("#deleteQuestionButton");
const cancelEditorButton = document.querySelector("#cancelEditorButton");
const saveQuestionBankButton = document.querySelector("#saveQuestionBankButton");
const closeManualEditorButton = document.querySelector("#closeManualEditorButton");

const excelImportDialog = document.querySelector("#excelImportDialog");
const importWritableBadge = document.querySelector("#importWritableBadge");
const importServerMessage = document.querySelector("#importServerMessage");
const importLoading = document.querySelector("#importLoading");
const importWorkspace = document.querySelector("#importWorkspace");
const excelFileInput = document.querySelector("#excelFileInput");
const selectedExcelFile = document.querySelector("#selectedExcelFile");
const cancelImportButton = document.querySelector("#cancelImportButton");
const uploadExcelButton = document.querySelector("#uploadExcelButton");

const editorLogic = window.Phase7QuestionEditor;
const editorState = {
  snapshot: null,
  draft: null,
  selectedIndex: 0,
  writable: false,
  busy: false,
};
const importState = {
  snapshot: null,
  file: null,
  writable: false,
  busy: false,
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = "No fue posible completar la acción.";
    let code = "";
    try {
      const payload = await response.json();
      code = payload.detail?.code || "";
      message = payload.detail?.message || payload.detail || message;
    } catch (_) {}
    const error = new Error(message);
    error.status = response.status;
    error.code = code;
    throw error;
  }
  return response.json();
}

async function uploadExcelBank(file, expectedRevision) {
  const params = new URLSearchParams({
    expected_revision: expectedRevision,
    filename: file.name,
  });
  const response = await fetch(`/api/questions/import?${params.toString()}`, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
    body: file,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail?.message || payload.detail || "No fue posible importar la base de preguntas.";
    const error = new Error(message);
    error.status = response.status;
    error.code = payload.detail?.code || "";
    throw error;
  }
  return payload;
}

function setMessage(element, text = "", className = "") {
  element.textContent = text;
  element.classList.toggle("success", className === "success");
}

function closeEditChoice() {
  editChoiceDialog.classList.add("hidden");
}

function showLogin() {
  closeEditChoice();
  closeManualEditor(true);
  closeExcelImport(true);
  loginView.classList.remove("hidden");
  dashboardView.classList.add("hidden");
  logoutButton.classList.add("hidden");
}

function showDashboard() {
  loginView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
  logoutButton.classList.remove("hidden");
  dashboardError.textContent = "";
}

function draftIsDirty() {
  return editorLogic.isDirty(editorState.snapshot, editorState.draft);
}

function selectedQuestion() {
  return editorState.draft?.questions?.[editorState.selectedIndex] || editorLogic.blankQuestion();
}

function setWritableBadge() {
  editorWritableBadge.classList.toggle("ok", editorState.writable);
  editorWritableBadge.classList.toggle("warning", !editorState.writable);
  editorWritableBadge.textContent = editorState.writable
    ? "Almacenamiento escribible"
    : "Sólo lectura: falta almacenamiento persistente";
}

function setImportWritableBadge() {
  importWritableBadge.classList.toggle("ok", importState.writable);
  importWritableBadge.classList.toggle("warning", !importState.writable);
  importWritableBadge.textContent = importState.writable
    ? "Almacenamiento escribible"
    : "Sólo lectura: falta almacenamiento persistente";
}

function setDirtyBadge() {
  const dirty = draftIsDirty();
  editorDirtyBadge.classList.toggle("hidden", !dirty);
  editorDirtyBadge.classList.toggle("dirty", dirty);
}

function validationSummary() {
  if (!editorState.draft) return { valid: false, errors: ["La base de preguntas aún no está cargada."] };
  return editorLogic.validateBank(editorState.draft);
}

function renderQuestionList() {
  const questions = editorState.draft?.questions || [];
  questionList.replaceChildren();
  questions.forEach((question, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = `question-list-button${index === editorState.selectedIndex ? " selected" : ""}`;
    const title = document.createElement("span");
    title.className = "question-list-title";
    title.textContent = question.prompt.trim() || "Pregunta sin enunciado";
    button.append(title);
    button.addEventListener("click", () => {
      editorState.selectedIndex = index;
      renderEditor();
    });
    item.append(button);
    questionList.append(item);
  });
  questionCount.textContent = `${questions.length} / ${editorLogic.REQUIRED_COUNT}`;
  questionListStatus.textContent = questions.length === editorLogic.REQUIRED_COUNT
    ? "Base de preguntas en cantidad requerida"
    : "Guardar requiere exactamente 12";
}

function renderForm() {
  const question = selectedQuestion();
  questionPrompt.value = question.prompt;
  promptCounter.textContent = `${question.prompt.length}/${editorLogic.PROMPT_LIMIT}`;
  answerInputs.forEach((input, index) => {
    input.value = question.answers[index] || "";
    answerCounters[index].textContent = `${input.value.length}/${editorLogic.ANSWER_LIMIT}`;
  });
  correctAnswer.value = String(question.correct_index);
}

function renderToolbar() {
  const total = editorState.draft?.questions?.length || 0;
  const hasSelection = total > 0;
  duplicateQuestionButton.disabled = !hasSelection;
  moveQuestionUpButton.disabled = !hasSelection || editorState.selectedIndex <= 0;
  moveQuestionDownButton.disabled = !hasSelection || editorState.selectedIndex >= total - 1;
  deleteQuestionButton.disabled = !hasSelection;

  const validation = validationSummary();
  saveQuestionBankButton.disabled = editorState.busy || !editorState.writable || !draftIsDirty() || !validation.valid;
  setMessage(editorValidationMessage, validation.valid ? "" : validation.errors[0]);
}

function renderEditor(options = {}) {
  if (!editorState.draft) return;
  setWritableBadge();
  setDirtyBadge();
  renderQuestionList();
  if (options.form !== false) renderForm();
  renderToolbar();
}

function openManualEditorShell() {
  closeEditChoice();
  manualEditorDialog.classList.remove("hidden");
  editorLoading.classList.remove("hidden");
  editorWorkspace.classList.add("hidden");
  setMessage(editorServerMessage, "");
  closeManualEditorButton.focus();
}

async function openManualEditor() {
  openManualEditorShell();
  try {
    const snapshot = await api("/api/questions");
    editorState.snapshot = snapshot;
    editorState.draft = editorLogic.cloneDraft(snapshot);
    editorState.selectedIndex = 0;
    editorState.writable = Boolean(snapshot.writable);
    editorLoading.classList.add("hidden");
    editorWorkspace.classList.remove("hidden");
    if (!editorState.writable) {
      setMessage(
        editorServerMessage,
        "El servidor informa modo sólo lectura. Puedes revisar o preparar cambios, pero no publicarlos hasta configurar almacenamiento persistente.",
      );
    }
    renderEditor();
    questionPrompt.focus();
  } catch (error) {
    editorLoading.classList.add("hidden");
    setMessage(editorServerMessage, error.message);
  }
}

function closeManualEditor(force = false) {
  if (!force && editorState.draft && draftIsDirty()) {
    const discard = window.confirm("Hay cambios sin guardar. ¿Quieres descartarlos?");
    if (!discard) return false;
  }
  manualEditorDialog.classList.add("hidden");
  editorState.snapshot = null;
  editorState.draft = null;
  editorState.selectedIndex = 0;
  editorState.busy = false;
  setMessage(editorServerMessage, "");
  return true;
}

function applyDraftUpdate(result) {
  editorState.draft = result.draft;
  editorState.selectedIndex = result.selectedIndex;
  setMessage(editorServerMessage, "");
  renderEditor();
}

function updateSelectedQuestion(patch) {
  editorState.draft = editorLogic.updateQuestion(editorState.draft, editorState.selectedIndex, patch);
  setMessage(editorServerMessage, "");
  setDirtyBadge();
  renderQuestionList();
  renderToolbar();
}

async function saveQuestionBank() {
  const validation = validationSummary();
  if (!validation.valid || !editorState.snapshot) {
    setMessage(editorValidationMessage, validation.errors[0]);
    return;
  }
  editorState.busy = true;
  renderToolbar();
  setMessage(editorServerMessage, "Guardando base de preguntas…", "success");
  try {
    const payload = editorLogic.serializeForPut(editorState.draft, editorState.snapshot.revision);
    const saved = await api("/api/questions", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    editorState.snapshot = saved;
    editorState.draft = editorLogic.cloneDraft(saved);
    editorState.writable = Boolean(saved.writable);
    editorState.selectedIndex = Math.min(editorState.selectedIndex, editorState.draft.questions.length - 1);
    setMessage(editorServerMessage, "Base de preguntas publicada correctamente.", "success");
  } catch (error) {
    if (error.status === 409) {
      setMessage(
        editorServerMessage,
        "La base de preguntas cambió en otra pestaña. Tu draft sigue abierto; recarga el editor antes de publicar para no sobrescribir cambios.",
      );
    } else if (error.status === 422) {
      setMessage(editorServerMessage, `Validación del servidor: ${error.message}`);
    } else if (error.status === 503 || error.code === "bank_read_only") {
      editorState.writable = false;
      setMessage(editorServerMessage, `Almacenamiento no escribible: ${error.message}`);
    } else {
      setMessage(editorServerMessage, error.message);
    }
  } finally {
    editorState.busy = false;
    renderEditor();
  }
}

function renderImportDialog() {
  setImportWritableBadge();
  selectedExcelFile.textContent = importState.file
    ? `Archivo seleccionado: ${importState.file.name}`
    : "Ningún archivo seleccionado.";
  uploadExcelButton.disabled = importState.busy || !importState.writable || !importState.file || !importState.snapshot;
}

function openExcelImportShell() {
  closeEditChoice();
  excelImportDialog.classList.remove("hidden");
  importLoading.classList.remove("hidden");
  importWorkspace.classList.add("hidden");
  importState.snapshot = null;
  importState.file = null;
  importState.busy = false;
  excelFileInput.value = "";
  setMessage(importServerMessage, "");
  cancelImportButton.focus();
}

async function openExcelImport() {
  openExcelImportShell();
  try {
    const snapshot = await api("/api/questions");
    importState.snapshot = snapshot;
    importState.writable = Boolean(snapshot.writable);
    importLoading.classList.add("hidden");
    importWorkspace.classList.remove("hidden");
    if (!importState.writable) {
      setMessage(
        importServerMessage,
        "El servidor informa modo sólo lectura. Puedes descargar la plantilla, pero no cargar bases de preguntas hasta configurar almacenamiento persistente.",
      );
    }
    renderImportDialog();
  } catch (error) {
    importLoading.classList.add("hidden");
    setMessage(importServerMessage, error.message);
  }
}

function closeExcelImport(force = false) {
  if (!force && importState.file) {
    const discard = window.confirm("Hay un archivo seleccionado. ¿Quieres cancelar la importación?");
    if (!discard) return false;
  }
  excelImportDialog.classList.add("hidden");
  importState.snapshot = null;
  importState.file = null;
  importState.busy = false;
  if (excelFileInput) excelFileInput.value = "";
  setMessage(importServerMessage, "");
  return true;
}

async function submitExcelImport() {
  if (!importState.file || !importState.snapshot) return;
  if (!importState.file.name.toLocaleLowerCase().endsWith(".xlsx")) {
    setMessage(importServerMessage, "El archivo debe tener extensión .xlsx.");
    return;
  }
  const confirmed = window.confirm("Esta acción reemplazará la base de preguntas actual completa si el Excel es válido. ¿Quieres continuar?");
  if (!confirmed) return;

  importState.busy = true;
  renderImportDialog();
  setMessage(importServerMessage, "Cargando base de preguntas…", "success");
  try {
    const saved = await uploadExcelBank(importState.file, importState.snapshot.revision);
    importState.snapshot = saved;
    importState.file = null;
    excelFileInput.value = "";
    setMessage(importServerMessage, "Base de preguntas importada correctamente.", "success");
  } catch (error) {
    if (error.status === 409) {
      setMessage(
        importServerMessage,
        "La base de preguntas cambió en otra pestaña. El archivo seleccionado no se cargó; recarga antes de intentar reemplazarla.",
      );
    } else if (error.status === 422) {
      setMessage(importServerMessage, `Validación del Excel: ${error.message}`);
    } else if (error.status === 503 || error.code === "bank_read_only") {
      importState.writable = false;
      setMessage(importServerMessage, `Almacenamiento no escribible: ${error.message}`);
    } else {
      setMessage(importServerMessage, error.message);
    }
  } finally {
    importState.busy = false;
    renderImportDialog();
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  try {
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ password: document.querySelector("#password").value }),
    });
    showDashboard();
  } catch (error) {
    loginError.textContent = error.message;
  }
});

createButton.addEventListener("click", async () => {
  dashboardError.textContent = "";
  createButton.disabled = true;
  const originalLabel = createButton.textContent;
  createButton.textContent = "Creando sala…";
  try {
    const game = await api("/api/games", {
      method: "POST",
      body: JSON.stringify({ bank_id: "main" }),
    });
    window.location.assign(`/host/${game.room_code}`);
  } catch (error) {
    dashboardError.textContent = error.message;
    createButton.disabled = false;
    createButton.textContent = originalLabel;
  }
});

editQuestionsButton.addEventListener("click", () => {
  editChoiceDialog.classList.remove("hidden");
  manualEditorButton.focus();
});

manualEditorButton.addEventListener("click", openManualEditor);
importExcelButton.addEventListener("click", openExcelImport);
closeEditChoiceButton.addEventListener("click", closeEditChoice);
editChoiceDialog.addEventListener("click", (event) => {
  if (event.target === editChoiceDialog) closeEditChoice();
});

newQuestionButton.addEventListener("click", () => {
  applyDraftUpdate(editorLogic.addQuestion(editorState.draft, editorState.selectedIndex));
});
duplicateQuestionButton.addEventListener("click", () => {
  applyDraftUpdate(editorLogic.duplicateQuestion(editorState.draft, editorState.selectedIndex));
});
moveQuestionUpButton.addEventListener("click", () => {
  applyDraftUpdate(editorLogic.moveQuestion(editorState.draft, editorState.selectedIndex, -1));
});
moveQuestionDownButton.addEventListener("click", () => {
  applyDraftUpdate(editorLogic.moveQuestion(editorState.draft, editorState.selectedIndex, 1));
});
deleteQuestionButton.addEventListener("click", () => {
  if (!window.confirm("¿Eliminar esta pregunta del draft?")) return;
  applyDraftUpdate(editorLogic.deleteQuestion(editorState.draft, editorState.selectedIndex));
});

questionPrompt.addEventListener("input", () => {
  updateSelectedQuestion({ prompt: questionPrompt.value });
  promptCounter.textContent = `${questionPrompt.value.length}/${editorLogic.PROMPT_LIMIT}`;
});
answerInputs.forEach((input, index) => {
  input.addEventListener("input", () => {
    updateSelectedQuestion({ answers: { [index]: input.value } });
    answerCounters[index].textContent = `${input.value.length}/${editorLogic.ANSWER_LIMIT}`;
  });
});
correctAnswer.addEventListener("change", () => {
  updateSelectedQuestion({ correct_index: Number(correctAnswer.value) });
});

cancelEditorButton.addEventListener("click", () => {
  closeManualEditor(false);
});
closeManualEditorButton.addEventListener("click", () => {
  closeManualEditor(false);
});
saveQuestionBankButton.addEventListener("click", saveQuestionBank);
manualEditorDialog.addEventListener("click", (event) => {
  if (event.target === manualEditorDialog) closeManualEditor(false);
});

excelFileInput.addEventListener("change", () => {
  const file = excelFileInput.files?.[0] || null;
  importState.file = file;
  setMessage(importServerMessage, "");
  if (file && !file.name.toLocaleLowerCase().endsWith(".xlsx")) {
    setMessage(importServerMessage, "El archivo debe tener extensión .xlsx.");
  }
  renderImportDialog();
});
cancelImportButton.addEventListener("click", () => {
  closeExcelImport(false);
});
uploadExcelButton.addEventListener("click", submitExcelImport);
excelImportDialog.addEventListener("click", (event) => {
  if (event.target === excelImportDialog) closeExcelImport(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (!manualEditorDialog.classList.contains("hidden")) closeManualEditor(false);
    else if (!excelImportDialog.classList.contains("hidden")) closeExcelImport(false);
    else closeEditChoice();
  }
});

window.addEventListener("beforeunload", (event) => {
  if (!editorState.draft || !draftIsDirty()) return;
  event.preventDefault();
  event.returnValue = "";
});

logoutButton.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST" });
  showLogin();
});

api("/api/auth/session").then(showDashboard).catch(showLogin);
