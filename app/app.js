const state = {
  ads: [],
  columns: [],
  brand: [],
  limits: [],
  templates: [],
  outputs: [],
  logoUrl: "",
  activeView: "copy",
  filters: { size: "All", design: "All" },
  saveTimer: null,
  pollingTimer: null,
};

const views = {
  copy: "Ad copy",
  brand: "Brand",
  templates: "Templates",
  preview: "Preview & generate",
  outputs: "Finished ads",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let data = {};
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `Request failed (${response.status})`);
  }
  return data;
}

function toast(message, type = "success") {
  const item = document.createElement("div");
  item.className = `toast ${type === "error" ? "error" : ""}`;
  item.textContent = message;
  $("#toastRegion").append(item);
  window.setTimeout(() => item.remove(), 3600);
}

function setSaveState(status, label) {
  const el = $("#saveState");
  el.className = `save-state ${status || ""}`;
  el.innerHTML = `<span></span>${label}`;
}

function navigate(view, updateHash = true) {
  if (!views[view]) return;
  state.activeView = view;
  $$(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
  $$("[data-view]").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  $("#breadcrumb").textContent = views[view];
  if (updateHash) history.replaceState(null, "", `#${view}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (view === "outputs") refreshOutputs();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));
}

function limitFor(field) {
  const row = state.limits.find((item) => item.field?.toLowerCase() === field.toLowerCase());
  return row ? { min: Number(row.min || 0), max: Number(row.max || 0) } : null;
}

function copyIssue(value, field) {
  const limit = limitFor(field);
  if (!limit) return "";
  const length = String(value || "").length;
  if (length < limit.min) return `${limit.min - length} characters under guidance`;
  if (length > limit.max) return `${length - limit.max} characters over guidance`;
  return "";
}

function fieldSpan(column) {
  if (column === "body") return "span-8";
  if (column === "hook") return "span-6";
  if (column === "designs" || column === "name" || column === "eyebrow") return "span-3";
  if (column === "cta" || column === "stat" || column === "stat_label") return "span-3";
  return "span-4";
}

function labelFor(column) {
  const labels = {
    designs: "Designs",
    name: "Internal name",
    eyebrow: "Category / eyebrow",
    hook: "Headline",
    body: "Supporting copy",
    cta: "Call to action",
    stat: "Proof point",
    stat_label: "Proof point label",
  };
  return labels[column] || column.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function inputFor(column, value, index) {
  const issue = copyIssue(value, column);
  const limit = limitFor(column);
  const isTextarea = column === "body" || column === "hook";
  const control = isTextarea
    ? `<textarea data-copy-field="${escapeHtml(column)}" data-index="${index}">${escapeHtml(value)}</textarea>`
    : `<input data-copy-field="${escapeHtml(column)}" data-index="${index}" value="${escapeHtml(value)}">`;
  const guidance = limit ? `${String(value || "").length} / ${limit.max}` : `${String(value || "").length} chars`;
  return `
    <div class="field ${fieldSpan(column)}">
      <label>${escapeHtml(labelFor(column))}</label>
      ${control}
      <div class="field-meta"><span class="${issue ? "issue" : ""}">${escapeHtml(issue || "Looks good")}</span><span>${guidance}</span></div>
    </div>`;
}

function renderCopy() {
  const list = $("#variationList");
  list.innerHTML = state.ads.map((ad, index) => `
    <article class="variation-card" data-index="${index}">
      <header class="variation-header">
        <div class="variation-title">
          <span class="variation-number">${String(index + 1).padStart(2, "0")}</span>
          <span class="variation-name">${escapeHtml(ad.name || ad.hook || `Variation ${index + 1}`)}</span>
        </div>
        <div class="variation-actions">
          <button title="Duplicate variation" aria-label="Duplicate variation ${index + 1}" data-duplicate="${index}">Duplicate</button>
          <button class="delete" title="Delete variation" aria-label="Delete variation ${index + 1}" data-delete="${index}">Delete</button>
        </div>
      </header>
      <div class="variation-fields">
        ${state.columns.map((column) => inputFor(column, ad[column] || "", index)).join("")}
      </div>
    </article>`).join("");
  updateCopySummary();
}

function updateCopySummary() {
  let issues = 0;
  state.ads.forEach((ad) => {
    state.columns.forEach((column) => { if (copyIssue(ad[column], column)) issues += 1; });
  });
  const sizeCount = new Set(state.templates.flatMap((item) => item.sizes)).size || 1;
  const designCount = state.templates.length || 1;
  $("#variationCount").textContent = state.ads.length;
  $("#copyIssueCount").textContent = issues;
  $("#estimatedOutputCount").textContent = state.ads.length * sizeCount * designCount;
}

function blankAd() {
  return Object.fromEntries(state.columns.map((column) => [column, column === "designs" ? "all" : ""]));
}

function addVariation(source = null) {
  state.ads.push(source ? { ...source, name: `${source.name || "variation"}-copy` } : blankAd());
  renderCopy();
  queueSaveAds();
  window.setTimeout(() => $(`.variation-card[data-index="${state.ads.length - 1}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
}

function queueSaveAds() {
  window.clearTimeout(state.saveTimer);
  setSaveState("saving", "Saving changes…");
  state.saveTimer = window.setTimeout(saveAds, 650);
}

async function saveAds() {
  try {
    await api("/api/save-ads", {
      method: "POST",
      body: JSON.stringify({ rows: state.ads, columns: state.columns }),
    });
    setSaveState("", "All changes saved");
    populatePreviewControls();
  } catch (error) {
    setSaveState("error", "Couldn’t save");
    toast(error.message, "error");
  }
}

function brandMap() {
  return Object.fromEntries(state.brand.map((row) => [row.token, row.value]));
}

function setBrandToken(token, value) {
  const existing = state.brand.find((row) => row.token === token);
  if (existing) existing.value = value;
  else state.brand.push({ token, value });
}

function renderBrand() {
  const brand = brandMap();
  const colors = [
    ["PRIMARY", "Primary"],
    ["PRIMARY_DARK", "Primary dark"],
    ["ACCENT", "Accent"],
    ["INK", "Ink"],
    ["MUTED", "Muted"],
  ];
  $("#colorGrid").innerHTML = colors.map(([token, label]) => {
    const value = brand[token] || "#000000";
    return `
      <div class="color-item">
        <input type="color" value="${escapeHtml(value)}" data-color-token="${token}" aria-label="${label} color">
        <div><label>${label}</label><input type="text" value="${escapeHtml(value)}" data-color-text="${token}" aria-label="${label} hex value"></div>
      </div>`;
  }).join("");
  $("#brandTokenList").innerHTML = state.brand.map((row, index) => `
    <div class="token-row">
      <input value="${escapeHtml(row.token)}" data-brand-token-name="${index}" aria-label="Brand token name">
      <input value="${escapeHtml(row.value)}" data-brand-token-value="${index}" aria-label="Brand token value">
      <button data-remove-token="${index}" aria-label="Remove ${escapeHtml(row.token)}">×</button>
    </div>`).join("");
  $("#brandPreview").style.setProperty("--preview-primary", brand.PRIMARY || "#e85d04");
  $("#brandPreview").style.setProperty("--preview-dark", brand.PRIMARY_DARK || "#4a1d09");
  $("#brandPreview").style.setProperty("--preview-accent", brand.ACCENT || "#ffb703");
  const logo = $("#brandLogoPreview");
  const fallback = $("#brandLogoFallback");
  if (state.logoUrl) {
    logo.src = `${state.logoUrl}?t=${Date.now()}`;
    logo.hidden = false;
    fallback.hidden = true;
  } else {
    logo.hidden = true;
    fallback.hidden = false;
  }
}

function renderLimits() {
  $("#limitsGrid").innerHTML = state.limits.map((row, index) => `
    <div class="limit-item">
      <strong>${escapeHtml(labelFor(row.field))}</strong>
      <label>Minimum<input type="number" min="0" value="${escapeHtml(row.min)}" data-limit-min="${index}"></label>
      <label>Maximum<input type="number" min="1" value="${escapeHtml(row.max)}" data-limit-max="${index}"></label>
    </div>`).join("");
}

async function saveBrand() {
  try {
    await api("/api/save-brand", { method: "POST", body: JSON.stringify({ rows: state.brand }) });
    setSaveState("", "All changes saved");
    toast("Brand settings saved.");
    renderBrand();
  } catch (error) { toast(error.message, "error"); }
}

async function saveLimits() {
  try {
    await api("/api/save-limits", { method: "POST", body: JSON.stringify({ rows: state.limits }) });
    toast("Copy guidance saved.");
    renderCopy();
  } catch (error) { toast(error.message, "error"); }
}

function renderTemplates() {
  $("#templateGrid").innerHTML = state.templates.map((template) => `
    <article class="template-card">
      <div class="template-thumb"><div class="mini-layout"><i></i><b></b></div></div>
      <div class="template-body">
        <div class="template-title-row"><div><h3>${escapeHtml(template.design)}</h3><small>${template.files.length} source file${template.files.length === 1 ? "" : "s"}</small></div><span>Ready</span></div>
        <div class="size-chips">${template.sizes.map((size) => `<span class="size-chip">${escapeHtml(size)}</span>`).join("")}</div>
        <div class="template-files">${template.files.map((file) => `<div class="template-file"><span title="${escapeHtml(file)}">${escapeHtml(file)}</span><button data-delete-template="${escapeHtml(file)}">Remove</button></div>`).join("")}</div>
        <div class="template-card-footer"><button class="button button-secondary compact" data-template-preview="${escapeHtml(template.design)}">Preview design</button></div>
      </div>
    </article>`).join("");
  populatePreviewControls();
  updateCopySummary();
}

function populatePreviewControls() {
  const rowSelect = $("#previewRowSelect");
  const currentRow = rowSelect.value;
  rowSelect.innerHTML = state.ads.map((ad, index) => `<option value="${index + 1}">${index + 1}. ${escapeHtml(ad.name || ad.hook || "Untitled variation")}</option>`).join("");
  if (currentRow && Number(currentRow) <= state.ads.length) rowSelect.value = currentRow;
  const designSelect = $("#previewDesignSelect");
  const currentDesign = designSelect.value;
  designSelect.innerHTML = state.templates.map((item) => `<option value="${escapeHtml(item.design)}">${escapeHtml(item.design)} · ${item.sizes.join(", ")}</option>`).join("");
  if (state.templates.some((item) => item.design === currentDesign)) designSelect.value = currentDesign;
}

async function saveBeforeRender() {
  window.clearTimeout(state.saveTimer);
  await saveAds();
  await api("/api/save-brand", { method: "POST", body: JSON.stringify({ rows: state.brand }) });
  await api("/api/save-limits", { method: "POST", body: JSON.stringify({ rows: state.limits }) });
}

async function refreshPreview() {
  const button = $("#refreshPreviewButton");
  button.disabled = true;
  button.textContent = "Rendering preview…";
  try {
    await saveBeforeRender();
    const row = Number($("#previewRowSelect").value || 1);
    const design = $("#previewDesignSelect").value;
    const result = await api("/api/preview", { method: "POST", body: JSON.stringify({ row, design }) });
    $("#previewImage").src = result.url;
    $("#previewStage").classList.add("has-image");
    $("#previewMeta").textContent = `${design} · variation ${row}`;
  } catch (error) {
    toast(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Refresh preview";
  }
}

async function startGeneration(proof) {
  try {
    await saveBeforeRender();
    await api("/api/generate", { method: "POST", body: JSON.stringify({ proof }) });
    $("#progressPanel").hidden = false;
    $("#jobTitle").textContent = proof ? "Generating quick proof" : "Generating full campaign";
    $("#proofButton").disabled = true;
    $("#generateButton").disabled = true;
    pollJob();
  } catch (error) { toast(error.message, "error"); }
}

async function pollJob() {
  window.clearTimeout(state.pollingTimer);
  try {
    const job = await api("/api/job");
    const progress = Number(job.progress || 0);
    $("#jobPercent").textContent = `${progress}%`;
    $("#progressBar").style.width = `${progress}%`;
    $("#jobMessage").textContent = job.message || "";
    if (job.status === "running") {
      state.pollingTimer = window.setTimeout(pollJob, 700);
    } else {
      $("#proofButton").disabled = false;
      $("#generateButton").disabled = false;
      if (job.status === "complete") {
        toast(job.message || "Your ads are ready.");
        await refreshOutputs();
        window.setTimeout(() => navigate("outputs"), 500);
      } else if (job.status === "error") {
        toast(job.message || "Generation failed.", "error");
      }
    }
  } catch (error) {
    toast(error.message, "error");
    $("#proofButton").disabled = false;
    $("#generateButton").disabled = false;
  }
}

function unique(items) { return [...new Set(items.filter(Boolean))]; }

function renderFilters() {
  const sizes = ["All", ...unique(state.outputs.map((item) => item.size))];
  const designs = ["All", ...unique(state.outputs.map((item) => item.design))];
  $("#sizeFilters").innerHTML = sizes.map((value) => `<button class="filter-chip ${state.filters.size === value ? "active" : ""}" data-size-filter="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("");
  $("#designFilters").innerHTML = designs.map((value) => `<button class="filter-chip ${state.filters.design === value ? "active" : ""}" data-design-filter="${escapeHtml(value)}">${escapeHtml(value)}</button>`).join("");
}

function renderOutputs() {
  renderFilters();
  const filtered = state.outputs.filter((item) =>
    (state.filters.size === "All" || item.size === state.filters.size)
    && (state.filters.design === "All" || item.design === state.filters.design));
  $("#outputResultCount").textContent = `${filtered.length} file${filtered.length === 1 ? "" : "s"}`;
  $("#outputNavCount").textContent = state.outputs.length;
  $("#outputEmpty").hidden = state.outputs.length > 0;
  $("#outputGrid").innerHTML = filtered.map((item, index) => `
    <article class="output-card">
      <button class="output-image" data-output-index="${state.outputs.indexOf(item)}" aria-label="Quick view ${escapeHtml(item.file)}">
        <img src="${escapeHtml(item.url)}?t=${item.modified}" loading="lazy" alt="${escapeHtml(item.design)} ad, ${escapeHtml(item.size)}">
        <span>${escapeHtml(item.size)}</span>
      </button>
      <div class="output-card-body">
        <div><strong>${escapeHtml(item.name || item.hook || `Variation ${item.row}`)}</strong><small>${escapeHtml(item.design)} · Row ${escapeHtml(item.row)}</small></div>
        <a class="download-button" href="${escapeHtml(item.url)}" download title="Download PNG">↓</a>
      </div>
    </article>`).join("");
}

async function refreshOutputs() {
  try {
    const result = await api("/api/outputs");
    state.outputs = result.outputs || [];
    renderOutputs();
  } catch (error) { toast(error.message, "error"); }
}

function openOutputModal(index) {
  const item = state.outputs[index];
  if (!item) return;
  $("#modalTitle").textContent = item.name || item.hook || `Variation ${item.row}`;
  $("#modalMeta").textContent = `${item.design} · ${item.size} · Row ${item.row}`;
  $("#modalImage").src = `${item.url}?t=${item.modified}`;
  $("#modalDownload").href = item.url;
  $("#imageModal").hidden = false;
  document.body.style.overflow = "hidden";
}

function closeModal() {
  $("#imageModal").hidden = true;
  document.body.style.overflow = "";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsDataURL(file);
  });
}

async function uploadFile(file, endpoint) {
  if (!file) return null;
  const data = await readFileAsDataUrl(file);
  return api(endpoint, { method: "POST", body: JSON.stringify({ name: file.name, data }) });
}

async function initialize() {
  try {
    const project = await api("/api/project");
    Object.assign(state, {
      ads: project.ads || [],
      columns: project.columns || [],
      brand: project.brand || [],
      limits: project.limits || [],
      templates: project.templates || [],
      outputs: project.outputs || [],
      logoUrl: project.logo_url || "",
    });
    renderCopy();
    renderBrand();
    renderLimits();
    renderTemplates();
    renderOutputs();
    populatePreviewControls();
    const browser = project.browser || {};
    $("#browserStatus").classList.toggle("error", !browser.ready);
    $("#browserStatus").innerHTML = `<span></span><div><strong>${browser.ready ? "Renderer ready" : "Renderer unavailable"}</strong><small>${escapeHtml(browser.message || "")}</small></div>`;
    if (project.job?.status === "running") {
      $("#progressPanel").hidden = false;
      pollJob();
    }
    const requested = location.hash.slice(1);
    navigate(views[requested] ? requested : "copy", false);
  } catch (error) {
    toast(`Could not load the project: ${error.message}`, "error");
  }
}

document.addEventListener("click", async (event) => {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) navigate(viewButton.dataset.view);

  const duplicate = event.target.closest("[data-duplicate]");
  if (duplicate) addVariation(state.ads[Number(duplicate.dataset.duplicate)]);

  const remove = event.target.closest("[data-delete]");
  if (remove) {
    const index = Number(remove.dataset.delete);
    const name = state.ads[index]?.name || `variation ${index + 1}`;
    if (confirm(`Delete “${name}”? This cannot be undone.`)) {
      state.ads.splice(index, 1);
      renderCopy();
      queueSaveAds();
    }
  }

  const removeToken = event.target.closest("[data-remove-token]");
  if (removeToken) {
    state.brand.splice(Number(removeToken.dataset.removeToken), 1);
    renderBrand();
  }

  const removeTemplate = event.target.closest("[data-delete-template]");
  if (removeTemplate) {
    const name = removeTemplate.dataset.deleteTemplate;
    if (confirm(`Remove template “${name}”?`)) {
      try {
        const result = await api("/api/delete-template", { method: "POST", body: JSON.stringify({ name }) });
        state.templates = result.templates;
        renderTemplates();
        toast("Template removed.");
      } catch (error) { toast(error.message, "error"); }
    }
  }

  const previewTemplate = event.target.closest("[data-template-preview]");
  if (previewTemplate) {
    navigate("preview");
    $("#previewDesignSelect").value = previewTemplate.dataset.templatePreview;
    refreshPreview();
  }

  const output = event.target.closest("[data-output-index]");
  if (output) openOutputModal(Number(output.dataset.outputIndex));
  if (event.target.closest("[data-close-modal]")) closeModal();

  const sizeFilter = event.target.closest("[data-size-filter]");
  if (sizeFilter) { state.filters.size = sizeFilter.dataset.sizeFilter; renderOutputs(); }
  const designFilter = event.target.closest("[data-design-filter]");
  if (designFilter) { state.filters.design = designFilter.dataset.designFilter; renderOutputs(); }
});

document.addEventListener("input", (event) => {
  const copy = event.target.closest("[data-copy-field]");
  if (copy) {
    const index = Number(copy.dataset.index);
    const field = copy.dataset.copyField;
    state.ads[index][field] = copy.value;
    const card = copy.closest(".variation-card");
    if (field === "name" || field === "hook") $(".variation-name", card).textContent = state.ads[index].name || state.ads[index].hook || `Variation ${index + 1}`;
    const meta = copy.parentElement.querySelector(".field-meta");
    const issue = copyIssue(copy.value, field);
    const limit = limitFor(field);
    meta.innerHTML = `<span class="${issue ? "issue" : ""}">${escapeHtml(issue || "Looks good")}</span><span>${copy.value.length}${limit ? ` / ${limit.max}` : " chars"}</span>`;
    updateCopySummary();
    queueSaveAds();
  }

  const color = event.target.closest("[data-color-token]");
  if (color) {
    setBrandToken(color.dataset.colorToken, color.value.toUpperCase());
    $(`[data-color-text="${color.dataset.colorToken}"]`).value = color.value.toUpperCase();
    renderBrand();
  }
  const colorText = event.target.closest("[data-color-text]");
  if (colorText && /^#[0-9a-f]{6}$/i.test(colorText.value)) {
    setBrandToken(colorText.dataset.colorText, colorText.value.toUpperCase());
    renderBrand();
  }
  const tokenName = event.target.closest("[data-brand-token-name]");
  if (tokenName) state.brand[Number(tokenName.dataset.brandTokenName)].token = tokenName.value;
  const tokenValue = event.target.closest("[data-brand-token-value]");
  if (tokenValue) state.brand[Number(tokenValue.dataset.brandTokenValue)].value = tokenValue.value;
  const limitMin = event.target.closest("[data-limit-min]");
  if (limitMin) state.limits[Number(limitMin.dataset.limitMin)].min = limitMin.value;
  const limitMax = event.target.closest("[data-limit-max]");
  if (limitMax) state.limits[Number(limitMax.dataset.limitMax)].max = limitMax.value;
});

$("#addVariationButton").addEventListener("click", () => addVariation());
$("#addVariationCard").addEventListener("click", () => addVariation());
$("#saveBrandButton").addEventListener("click", saveBrand);
$("#saveLimitsButton").addEventListener("click", saveLimits);
$("#addBrandTokenButton").addEventListener("click", () => { state.brand.push({ token: "NEW_TOKEN", value: "" }); renderBrand(); });
$("#refreshPreviewButton").addEventListener("click", refreshPreview);
$("#proofButton").addEventListener("click", () => startGeneration(true));
$("#generateButton").addEventListener("click", () => startGeneration(false));
$("#openTemplatesButton").addEventListener("click", () => api("/api/open-folder", { method: "POST", body: JSON.stringify({ target: "templates" }) }).catch((error) => toast(error.message, "error")));
$("#openOutputsButton").addEventListener("click", () => api("/api/open-folder", { method: "POST", body: JSON.stringify({ target: "outputs" }) }).catch((error) => toast(error.message, "error")));

$("#adsImportInput").addEventListener("change", async (event) => {
  try {
    const result = await uploadFile(event.target.files[0], "/api/import-ads");
    if (result) {
      state.ads = result.rows;
      state.columns = result.columns;
      renderCopy();
      populatePreviewControls();
      toast(`Imported ${state.ads.length} copy variations.`);
    }
  } catch (error) { toast(error.message, "error"); }
  event.target.value = "";
});

$("#logoInput").addEventListener("change", async (event) => {
  try {
    const result = await uploadFile(event.target.files[0], "/api/upload-logo");
    if (result) {
      state.brand = result.brand;
      state.logoUrl = result.logo_url;
      renderBrand();
      toast("Logo updated.");
    }
  } catch (error) { toast(error.message, "error"); }
  event.target.value = "";
});

$("#templateInput").addEventListener("change", async (event) => {
  try {
    const result = await uploadFile(event.target.files[0], "/api/upload-template");
    if (result) {
      state.templates = result.templates;
      renderTemplates();
      toast("Template added.");
    }
  } catch (error) { toast(error.message, "error"); }
  event.target.value = "";
});

const dropzone = $("#logoDropzone");
["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.add("dragging"); }));
["dragleave", "drop"].forEach((name) => dropzone.addEventListener(name, (event) => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
dropzone.addEventListener("drop", async (event) => {
  try {
    const result = await uploadFile(event.dataTransfer.files[0], "/api/upload-logo");
    state.brand = result.brand; state.logoUrl = result.logo_url; renderBrand(); toast("Logo updated.");
  } catch (error) { toast(error.message, "error"); }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("#imageModal").hidden) closeModal();
});

initialize();
