import { makeMessage, MESSAGE_TYPES } from "../messaging/messages.js";

document.addEventListener("DOMContentLoaded", init);

async function init() {
  document.getElementById("version").textContent = chrome.runtime.getManifest().version;
  document.getElementById("save").addEventListener("click", save);
  document.getElementById("test").addEventListener("click", test);
  document.getElementById("clear").addEventListener("click", clear);
  const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.GET_SETTINGS));
  if (response.ok) fill(response.payload);
}

function fill(settings) {
  document.getElementById("backend-url").value = settings.backendUrl || "http://127.0.0.1:8000";
  document.getElementById("extension-token").value = settings.extensionApiToken || "local-token";
}

async function save() {
  const payload = {
    backendUrl: document.getElementById("backend-url").value.trim(),
    extensionApiToken: document.getElementById("extension-token").value
  };
  const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.SAVE_SETTINGS, payload));
  setMessage(response.ok ? "Settings saved." : response.error.message);
}

async function test() {
  await save();
  const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.TEST_CONNECTION));
  setMessage(response.ok ? "Connected to Alduor" : "Could not connect to the Alduor backend. Check that FastAPI is running and the local token is correct.");
}

async function clear() {
  await chrome.storage.local.clear();
  fill({ backendUrl: "http://127.0.0.1:8000", extensionApiToken: "local-token" });
  setMessage("Settings cleared.");
}

function setMessage(message) {
  document.getElementById("message").textContent = message;
}

