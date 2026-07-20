import { MESSAGE_TYPES, PROTOCOL_VERSION } from "./messages.js";

export function validateMessage(message, sender) {
  if (!sender || sender.id !== chrome.runtime.id) {
    throw new Error("INVALID_SENDER");
  }
  if (!message || typeof message !== "object") {
    throw new Error("INVALID_MESSAGE");
  }
  if (!Object.values(MESSAGE_TYPES).includes(message.type)) {
    throw new Error("UNKNOWN_MESSAGE_TYPE");
  }
  if (message.protocol_version !== PROTOCOL_VERSION) {
    throw new Error("INVALID_PROTOCOL_VERSION");
  }
  if (!message.request_id || typeof message.request_id !== "string") {
    throw new Error("INVALID_REQUEST_ID");
  }
  if (message.payload && typeof message.payload !== "object") {
    throw new Error("INVALID_PAYLOAD");
  }
}

