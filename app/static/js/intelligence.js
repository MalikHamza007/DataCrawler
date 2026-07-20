(function () {
  let view = "classifications";

  function button(label, handler) {
    const element = document.createElement("button"); element.type = "button"; element.className = "secondary-button"; element.textContent = label; element.addEventListener("click", handler); return element;
  }

  async function load() {
    const root = document.getElementById("intelligence-results"); root.textContent = "Loading...";
    try {
      const records = view === "classifications" ? await AlduorApi.listAssessments() : view === "relationships" ? await AlduorApi.listRelationships() : await AlduorApi.listDuplicates();
      root.textContent = "";
      if (!records.length) { root.textContent = "No review items."; return; }
      records.forEach((record) => root.appendChild(render(record)));
    } catch (error) { root.textContent = error.message; }
  }

  function render(record) {
    const row = document.createElement("div"); row.className = "intelligence-row";
    const summary = document.createElement("div");
    const actions = document.createElement("div"); actions.className = "button-row";
    if (view === "classifications") {
      summary.textContent = `${record.entity_type} #${record.developer_id || record.project_id}: ${record.suggested_classification} | ${record.system_score} | ${record.confidence_level} | ${record.assessment_status}`;
      actions.append(button("Confirm", async () => { await AlduorApi.reviewAssessment(record.id, "confirm", { review_note: "Confirmed in intelligence review" }); load(); }), button("Override", async () => { const classification = window.prompt("Manual classification"); const note = classification && window.prompt("Review note"); if (classification && note) { await AlduorApi.reviewAssessment(record.id, "override", { manual_classification: classification, review_note: note }); load(); } }), button("Reject", async () => { await AlduorApi.reviewAssessment(record.id, "reject", { review_note: "Rejected in intelligence review" }); load(); }));
    } else if (view === "relationships") {
      summary.textContent = `Project #${record.project_id} -> Developer #${record.developer_id}: ${record.system_score ?? 0} | ${record.confidence_level || "unscored"} | ${record.status}`;
      actions.append(button("Recalculate", async () => { await AlduorApi.reviewRelationship(record.id, "recalculate"); load(); }), button("Verify", async () => { await AlduorApi.reviewRelationship(record.id, "verify", { review_note: "Verified in intelligence review" }); load(); }), button("Reject", async () => { await AlduorApi.reviewRelationship(record.id, "reject", { review_note: "Rejected in intelligence review" }); load(); }));
    } else {
      const left = record.left_developer_id || record.left_project_id; const right = record.right_developer_id || record.right_project_id;
      summary.textContent = `${record.entity_type} #${left} vs #${right}: ${record.duplicate_score} | ${record.confidence_level} | ${record.status}`;
      const preview = async (survivor) => { const result = await AlduorApi.reviewDuplicate(record.id, "merge-preview", { survivor_id: survivor }); window.AlduorApp.notify(`Merge preview: #${result.survivor_id} keeps, #${result.absorbed_id} merges`, "success"); };
      const merge = async (survivor) => { if (window.confirm(`Merge this pair with #${survivor} as survivor?`)) { await AlduorApi.reviewDuplicate(record.id, "merge", { survivor_id: survivor, operator_note: "Confirmed in intelligence review" }); load(); } };
      actions.append(button("Confirm", async () => { await AlduorApi.reviewDuplicate(record.id, "confirm", { review_note: "Confirmed duplicate" }); load(); }), button("Not duplicate", async () => { await AlduorApi.reviewDuplicate(record.id, "not-duplicate", { review_note: "Records are distinct" }); load(); }), button("Preview left", () => preview(left)), button("Preview right", () => preview(right)), button("Merge left", () => merge(left)), button("Merge right", () => merge(right)));
    }
    const detail = document.createElement("pre"); detail.textContent = JSON.stringify({ explanation: record.explanation, signals: record.signals_json }, null, 2);
    row.append(summary, actions, detail); return row;
  }

  document.querySelectorAll(".intelligence-tab").forEach((tab) => tab.addEventListener("click", () => { document.querySelectorAll(".intelligence-tab").forEach((item) => item.classList.remove("is-active")); tab.classList.add("is-active"); view = tab.dataset.view; load(); }));
  document.getElementById("refresh-intelligence").addEventListener("click", load);
  load();
})();
