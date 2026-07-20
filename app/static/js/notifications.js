export function notify(message) {
  const element = document.getElementById("notification");
  element.textContent = message;
  element.classList.add("is-visible");
  window.setTimeout(() => element.classList.remove("is-visible"), 3500);
}

