export function text(value, fallback = "") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

export function date(value) {
  return value ? new Date(value).toLocaleString() : "";
}

export function badge(value) {
  const span = document.createElement("span");
  span.className = `badge ${String(value || "").replaceAll(" ", "_")}`;
  span.textContent = text(value, "unknown").replaceAll("_", " ");
  return span;
}

export function safeLink(url, label = "Open source") {
  const link = document.createElement("a");
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("unsafe");
    link.href = parsed.href;
    link.textContent = label;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  } catch (_) {
    link.textContent = "Invalid URL";
  }
  return link;
}

export function td(value) {
  const cell = document.createElement("td");
  if (value instanceof Node) cell.appendChild(value);
  else cell.textContent = text(value);
  return cell;
}

