(function () {
  async function init() {
    const button = document.getElementById("refresh-social-captures");
    if (!button) return;
    button.addEventListener("click", loadCaptures);
    await loadCaptures();
  }

  async function loadCaptures() {
    const body = document.getElementById("social-captures-body");
    const empty = document.getElementById("social-captures-empty");
    body.textContent = "";
    try {
      const captures = await window.AlduorApi.listSocialCaptures();
      empty.hidden = captures.length > 0;
      captures.forEach((capture) => body.appendChild(row(capture)));
    } catch (error) {
      empty.hidden = false;
      empty.textContent = error.message;
    }
  }

  function row(capture) {
    const tr = document.createElement("tr");
    tr.append(
      cell(capture.platform),
      cell(capture.profile_name || capture.page_title || "Unnamed capture"),
      cell(capture.page_kind),
      cell(targetLabel(capture)),
      cell(new Date(capture.captured_at).toLocaleString()),
      cell(capture.review_status),
      sourceCell(capture.source_url),
      actionsCell(capture)
    );
    return tr;
  }

  function cell(value) {
    const td = document.createElement("td");
    td.textContent = value || "";
    return td;
  }

  function sourceCell(url) {
    const td = document.createElement("td");
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = "Open source";
    td.appendChild(link);
    return td;
  }

  function actionsCell(capture) {
    const td = document.createElement("td");
    td.className = "compact-actions";
    [
      ["accept", "Accept"],
      ["reject", "Reject"],
      ["mark-duplicate", "Mark duplicate"]
    ].forEach(([action, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary-button";
      button.textContent = label;
      button.addEventListener("click", async () => {
        try {
          await window.AlduorApi.reviewSocialCapture(capture.id, action, { review_note: "" });
          window.AlduorApp.notify("Capture updated.", "success");
          await loadCaptures();
        } catch (error) {
          window.AlduorApp.notify(error.message, "error");
        }
      });
      td.appendChild(button);
    });
    return td;
  }

  function targetLabel(capture) {
    const parts = [];
    if (capture.developer_id) parts.push(`Developer #${capture.developer_id}`);
    if (capture.project_id) parts.push(`Project #${capture.project_id}`);
    return parts.join(", ") || "Unassigned";
  }

  window.addEventListener("DOMContentLoaded", init);
})();
