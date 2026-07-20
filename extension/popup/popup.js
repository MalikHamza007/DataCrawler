import { makeMessage, MESSAGE_TYPES } from "../messaging/messages.js";
import { fieldsFromCapture, renderPreview } from "./preview.js";
import { searchEntities } from "./entity-search.js";

let currentCapture = null;
let currentFields = [];
let selectedDeveloperId = null;
let selectedProjectId = null;
let capturing = false;

document.addEventListener("DOMContentLoaded", init);

async function init() {
  await describeCurrentTab();
  document.getElementById("capture-button").addEventListener("click", captureCurrentPage);
  document.getElementById("save-button").addEventListener("click", saveCapture);
  document.getElementById("entity-query").addEventListener("input", debounce(loadEntities, 250));
  document.getElementById("entity-type").addEventListener("change", loadEntities);
  testConnection();
}

async function describeCurrentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab && tab.url ? tab.url : "";
  document.getElementById("page-url").textContent = url || "Unavailable";
  const detected = detectFromUrl(url);
  document.getElementById("platform").textContent = detected.platform;
  document.getElementById("page-kind").textContent = detected.page_kind;
}

async function testConnection() {
  const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.TEST_CONNECTION));
  document.getElementById("backend-status").textContent = response.ok ? "Connected to Alduor" : "Could not connect";
}

async function captureCurrentPage() {
  if (capturing) return;
  capturing = true;
  const button = document.getElementById("capture-button");
  button.disabled = true;
  setMessage("");
  try {
    button.textContent = "Reading Visible Page...";
    const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.CAPTURE_ACTIVE_PAGE));
    if (!response.ok) throw new Error(response.error.message);
    if (response.payload.supported === false) throw new Error("This page type is not supported for Alduor business capture. Open a public business Page, project profile, public post or Ad Library result.");
    currentCapture = response.payload;
    currentFields = fieldsFromCapture(currentCapture);
    button.textContent = "Preparing Preview...";
    renderPreview(document.getElementById("preview"), currentCapture);
    document.getElementById("target-panel").hidden = false;
    document.getElementById("platform").textContent = currentCapture.platform;
    document.getElementById("page-kind").textContent = currentCapture.page_kind;
  } catch (error) {
    setMessage(`${error.message} Code: CAPTURE_ERROR`);
  } finally {
    capturing = false;
    button.disabled = false;
    button.textContent = "Capture Current Page";
  }
}

async function loadEntities() {
  const q = document.getElementById("entity-query").value.trim();
  const results = document.getElementById("entity-results");
  results.textContent = "";
  if (q.length < 2) return;
  try {
    const items = await searchEntities(q, document.getElementById("entity-type").value);
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "entity-button";
      button.textContent = `${item.entity_type}: ${item.name}${item.subtitle ? " | " + item.subtitle : ""}`;
      button.addEventListener("click", () => {
        if (item.entity_type === "developer") selectedDeveloperId = item.id;
        if (item.entity_type === "project") selectedProjectId = item.id;
        renderTargets();
      });
      results.appendChild(button);
    });
  } catch (error) {
    setMessage(error.message);
  }
}

async function saveCapture() {
  if (!currentCapture) return;
  syncFieldEdits();
  const payload = {
    capture: currentCapture,
    selected_fields: currentFields,
    developer_id: selectedDeveloperId,
    project_id: selectedProjectId,
    extension_version: chrome.runtime.getManifest().version,
    operator_note: document.getElementById("operator-note").value.trim() || null
  };
  const button = document.getElementById("save-button");
  button.disabled = true;
  try {
    const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.SUBMIT_CAPTURE, payload));
    if (!response.ok) throw new Error(response.error.message);
    setMessage(`Saved capture #${response.payload.id}.`);
  } catch (error) {
    setMessage(`${error.message} Code: SUBMIT_CAPTURE`);
  } finally {
    button.disabled = false;
  }
}

function syncFieldEdits() {
  document.querySelectorAll(".field-row").forEach((row) => {
    const checkbox = row.querySelector("input[type='checkbox']");
    const input = row.querySelector("input[type='text']");
    const index = Number(input.dataset.fieldIndex);
    currentFields[index].include = checkbox.checked;
    currentFields[index].submitted_value = input.value.trim();
  });
}

function renderTargets() {
  const parts = [];
  if (selectedDeveloperId) parts.push(`Developer #${selectedDeveloperId}`);
  if (selectedProjectId) parts.push(`Project #${selectedProjectId}`);
  document.getElementById("selected-targets").textContent = parts.join(", ") || "No target selected. Capture will be saved to the inbox.";
}

function detectFromUrl(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.replace(/^www\./, "");
    if ((host === "facebook.com" || host === "m.facebook.com") && url.pathname.startsWith("/ads/library")) return { platform: "meta_ad_library", page_kind: "ad_library_result" };
    if (host === "facebook.com" || host === "m.facebook.com") return { platform: "facebook", page_kind: "unknown" };
    if (host === "instagram.com") return { platform: "instagram", page_kind: "unknown" };
    if (host === "x.com" || host === "twitter.com") return { platform: "x", page_kind: "unknown" };
    if (host === "linkedin.com") return { platform: "linkedin", page_kind: "unknown" };
  } catch (_) {
    return { platform: "unsupported", page_kind: "unknown" };
  }
  return { platform: "generic", page_kind: "unknown_public_page" };
}

function debounce(fn, wait) {
  let timer = 0;
  return () => {
    clearTimeout(timer);
    timer = setTimeout(fn, wait);
  };
}

function setMessage(message) {
  document.getElementById("message").textContent = message;
}

