export const PROTOCOL_VERSION = "1";
export const MESSAGE_TYPES = Object.freeze({
  GET_SETTINGS: "GET_SETTINGS",
  SAVE_SETTINGS: "SAVE_SETTINGS",
  TEST_CONNECTION: "TEST_CONNECTION",
  CAPTURE_ACTIVE_PAGE: "CAPTURE_ACTIVE_PAGE",
  SEARCH_ENTITIES: "SEARCH_ENTITIES",
  SUBMIT_CAPTURE: "SUBMIT_CAPTURE"
});

export function makeMessage(type, payload = {}) {
  return {
    type,
    protocol_version: PROTOCOL_VERSION,
    request_id: crypto.randomUUID(),
    payload
  };
}

