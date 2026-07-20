export function fieldsFromCapture(capture) {
  const fields = [];
  add(fields, "profile_name", "Identity", capture.profile_name);
  add(fields, "username", "Identity", capture.username);
  add(fields, "visible_text_excerpt", "Description", capture.visible_text_excerpt);
  add(fields, "about_text", "About", capture.about_text);
  (capture.project_names || []).forEach((value) => add(fields, "project_name", "Project", value));
  (capture.phones || []).forEach((item) => add(fields, "phone", item.label || "Phone", item.value));
  (capture.emails || []).forEach((item) => add(fields, "email", item.label || "Email", item.value));
  (capture.whatsapp || []).forEach((item) => add(fields, "whatsapp", "WhatsApp", item.value || item.url));
  (capture.addresses || []).forEach((value) => add(fields, "address", "Address", value));
  (capture.websites || []).forEach((value) => add(fields, "official_website", "Website", value));
  if (capture.campaign) {
    add(fields, "campaign_text", "Campaign", capture.campaign.campaign_text);
    add(fields, "campaign_cta", "Campaign", capture.campaign.call_to_action);
    add(fields, "campaign_destination", "Campaign", capture.campaign.destination_url);
  }
  return fields;
}

function add(fields, fieldName, sourceLabel, value) {
  const text = String(value || "").trim();
  if (!text) return;
  fields.push({ field_name: fieldName, source_label: sourceLabel, original_extracted_value: text, submitted_value: text, include: true, target_entity: "both" });
}

export function renderPreview(container, capture) {
  container.hidden = false;
  container.textContent = "";
  const heading = document.createElement("h2");
  heading.textContent = "Preview and correction";
  container.appendChild(heading);
  const source = document.createElement("p");
  source.textContent = `${capture.platform} | ${capture.page_kind} | ${capture.source_url}`;
  container.appendChild(source);
  const warnings = capture.warnings || [];
  if (warnings.length) {
    const title = document.createElement("div");
    title.className = "section-title";
    title.textContent = "Warnings";
    container.appendChild(title);
    warnings.forEach((warning) => {
      const p = document.createElement("p");
      p.textContent = warning;
      container.appendChild(p);
    });
  }
  fieldsFromCapture(capture).forEach((field, index) => container.appendChild(fieldRow(field, index)));
}

function fieldRow(field, index) {
  const row = document.createElement("label");
  row.className = "field-row";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = true;
  checkbox.dataset.fieldIndex = String(index);
  const label = document.createElement("span");
  label.textContent = field.source_label;
  const input = document.createElement("input");
  input.type = "text";
  input.value = field.submitted_value;
  input.dataset.fieldIndex = String(index);
  row.append(checkbox, label, input);
  return row;
}
