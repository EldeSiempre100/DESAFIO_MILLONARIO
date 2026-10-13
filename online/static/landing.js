const form = document.querySelector("#roomForm");
const codeInput = document.querySelector("#roomCode");
const error = document.querySelector("#roomError");

codeInput.addEventListener("input", () => {
  codeInput.value = codeInput.value.replace(/\D/g, "").slice(0, 6);
  error.textContent = "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = codeInput.value.trim();
  if (!/^\d{6}$/.test(code)) {
    error.textContent = "Ingresa los seis dígitos de la sala.";
    return;
  }
  try {
    const response = await fetch(`/api/rooms/${code}/bootstrap`);
    if (!response.ok) throw new Error("La sala no existe o ya finalizó.");
    window.location.assign(`/join/${code}`);
  } catch (requestError) {
    error.textContent = requestError.message;
  }
});
