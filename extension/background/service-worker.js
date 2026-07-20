import { MESSAGE_TYPES } from "../messaging/messages.js";
import { validateMessage } from "../messaging/validators.js";

const DEFAULT_SETTINGS = {
  backendUrl: "http://127.0.0.1:8000",
  extensionApiToken: "local-token"
};

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender).then(sendResponse).catch((error) => {
    sendResponse({ ok: false, error: normalizeError(error) });
  });
  return true;
});

async function handleMessage(message, sender) {
  validateMessage(message, sender);
  if (message.type === MESSAGE_TYPES.GET_SETTINGS) return { ok: true, payload: await getSettings() };
  if (message.type === MESSAGE_TYPES.SAVE_SETTINGS) return { ok: true, payload: await saveSettings(message.payload) };
  if (message.type === MESSAGE_TYPES.TEST_CONNECTION) return { ok: true, payload: await apiRequest("/api/extension/status") };
  if (message.type === MESSAGE_TYPES.SEARCH_ENTITIES) return { ok: true, payload: await searchEntities(message.payload) };
  if (message.type === MESSAGE_TYPES.SUBMIT_CAPTURE) return { ok: true, payload: await submitCapture(message.payload) };
  if (message.type === MESSAGE_TYPES.CAPTURE_ACTIVE_PAGE) return { ok: true, payload: await captureActivePage() };
  return { ok: false, error: { code: "UNKNOWN_MESSAGE_TYPE", message: "Unknown extension message." } };
}

async function getSettings() {
  const stored = await chrome.storage.local.get(DEFAULT_SETTINGS);
  return {
    backendUrl: sanitizeBackendUrl(stored.backendUrl || DEFAULT_SETTINGS.backendUrl),
    extensionApiToken: String(stored.extensionApiToken || DEFAULT_SETTINGS.extensionApiToken)
  };
}

async function saveSettings(payload) {
  const settings = {
    backendUrl: sanitizeBackendUrl(payload.backendUrl || DEFAULT_SETTINGS.backendUrl),
    extensionApiToken: String(payload.extensionApiToken || "")
  };
  await chrome.storage.local.set(settings);
  return settings;
}

async function searchEntities(payload) {
  const query = new URLSearchParams({
    q: String(payload.q || ""),
    entity_type: String(payload.entity_type || "all"),
    limit: String(Math.min(Number(payload.limit || 10), 25)),
    include_merged: payload.include_merged ? "true" : "false"
  });
  return apiRequest(`/api/entities/search?${query.toString()}`);
}

async function submitCapture(payload) {
  return apiRequest("/api/social-captures", { method: "POST", body: JSON.stringify(payload) });
}

async function captureActivePage() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id || !tab.url || tab.url.startsWith("chrome:") || tab.url.startsWith("chrome-extension:")) {
    throw Object.assign(new Error("This page type is not supported for Alduor business capture."), { code: "UNSUPPORTED_PAGE" });
  }
  const files = [
    "extractors/common.js",
    "extractors/normalizers.js",
    "extractors/platform-detector.js",
    "extractors/generic.js",
    "extractors/facebook.js",
    "extractors/instagram.js",
    "extractors/x.js",
    "extractors/linkedin.js",
    "extractors/meta-ad-library.js"
  ];
  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files });
  const [result] = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => window.AlduorExtractors.captureVisiblePage()
  });
  return result.result;
}

async function apiRequest(path, options = {}) {
  const settings = await getSettings();
  const response = await fetch(`${settings.backendUrl}${path}`, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Alduor-Extension-Token": settings.extensionApiToken
    },
    body: options.body
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const error = new Error(data && data.detail ? String(data.detail) : "Could not connect to the Alduor backend.");
    error.code = response.status === 401 || response.status === 403 ? "INVALID_EXTENSION_TOKEN" : `HTTP_${response.status}`;
    throw error;
  }
  return data;
}

function sanitizeBackendUrl(value) {
  const url = new URL(String(value));
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("INVALID_BACKEND_URL");
  return url.origin;
}

function normalizeError(error) {
  return {
    code: error.code || error.message || "CAPTURE_ERROR",
    message: error.message || "The extension request failed."
  };
}

