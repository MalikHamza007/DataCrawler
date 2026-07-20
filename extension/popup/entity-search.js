import { makeMessage, MESSAGE_TYPES } from "../messaging/messages.js";

export async function searchEntities(q, entityType) {
  const response = await chrome.runtime.sendMessage(makeMessage(MESSAGE_TYPES.SEARCH_ENTITIES, { q, entity_type: entityType, limit: 10 }));
  if (!response.ok) throw new Error(response.error.message);
  return response.payload.items || [];
}
