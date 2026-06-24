const form = document.getElementById("scan-form");
const submitBtn = document.getElementById("submit-btn");
const spinner = document.getElementById("spinner");
const loadingStatus = document.getElementById("loading-status");
const loadingLabel = document.getElementById("loading-label");
const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");
const errorCode = document.getElementById("error-code");
const errorRetry = document.getElementById("error-retry");
const resultsPanel = document.getElementById("results");

const LOADING_STAGES = [
  "Validating URL…",
  "Fetching product page…",
  "Extracting fitment data…",
  "Analyzing compatibility…",
];

let loadingTimer = null;

function setLoading(loading) {
  submitBtn.disabled = loading;
  spinner.classList.toggle("hidden", !loading);
  loadingStatus.classList.toggle("hidden", !loading);

  if (loading) {
    let stage = 0;
    loadingLabel.textContent = LOADING_STAGES[0];
    loadingTimer = window.setInterval(() => {
      stage = Math.min(stage + 1, LOADING_STAGES.length - 1);
      loadingLabel.textContent = LOADING_STAGES[stage];
    }, 4500);
  } else if (loadingTimer) {
    window.clearInterval(loadingTimer);
    loadingTimer = null;
  }
}

function hidePanels() {
  errorPanel.classList.add("hidden");
  resultsPanel.classList.add("hidden");
}

function showError(message, code) {
  errorMessage.textContent = message;
  errorCode.textContent = code ? `Code: ${code}` : "";
  errorPanel.classList.remove("hidden");
  resultsPanel.classList.add("hidden");
  errorPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function formatConfidence(confidence) {
  if (!confidence || confidence === "none") return "";
  return confidence.charAt(0).toUpperCase() + confidence.slice(1) + " confidence";
}

function formatMs(ms) {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)} s`;
  }
  return `${Math.round(ms)} ms`;
}

function formatTimingLabel(key) {
  return key
    .replace(/_ms$/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function renderResults(data) {
  const { product, compatibility, timings } = data;
  const verdictHeader = document.getElementById("verdict-header");
  const verdictIcon = document.getElementById("verdict-icon");
  const verdictLabel = document.getElementById("verdict-label");
  const badge = document.getElementById("compatibility-badge");
  const summary = document.getElementById("summary");

  verdictHeader.className = "verdict-header";

  if (compatibility.compatible === true) {
    verdictHeader.classList.add("compatible");
    verdictIcon.textContent = "✓";
    verdictLabel.textContent = "Compatible";
    badge.textContent = formatConfidence(compatibility.confidence) || "Likely fits your vehicle";
  } else if (compatibility.compatible === false) {
    verdictHeader.classList.add("incompatible");
    verdictIcon.textContent = "✕";
    verdictLabel.textContent = "Not compatible";
    badge.textContent = formatConfidence(compatibility.confidence) || "Does not appear to fit";
  } else {
    verdictHeader.classList.add("unknown");
    verdictIcon.textContent = "?";
    verdictLabel.textContent = "Unclear";
    badge.textContent = formatConfidence(compatibility.confidence) || "Not enough fitment data";
  }

  summary.textContent = compatibility.summary || "No summary available.";

  const productDetails = document.getElementById("product-details");
  productDetails.innerHTML = "";
  const fields = [
    ["Name", product.name],
    ["Brand", product.brand],
    ["SKU", product.sku],
    ["Category", product.category],
    ["Description", product.description],
  ];
  for (const [label, value] of fields) {
    if (value) {
      productDetails.innerHTML += `<dt>${label}</dt><dd>${escapeHtml(value)}</dd>`;
    }
  }

  const matchedList = document.getElementById("matched-vehicles");
  const matchedSection = document.getElementById("matched-section");
  matchedList.innerHTML = "";
  if (compatibility.matched_vehicles?.length) {
    matchedSection.classList.remove("hidden");
    for (const v of compatibility.matched_vehicles) {
      matchedList.innerHTML += `<li>${escapeHtml(v)}</li>`;
    }
  } else {
    matchedSection.classList.add("hidden");
  }

  const notesList = document.getElementById("notes");
  const notesSection = document.getElementById("notes-section");
  notesList.innerHTML = "";
  if (compatibility.notes?.length) {
    notesSection.classList.remove("hidden");
    for (const n of compatibility.notes) {
      notesList.innerHTML += `<li>${escapeHtml(n)}</li>`;
    }
  } else {
    notesSection.classList.add("hidden");
  }

  const timingsEl = document.getElementById("timings");
  timingsEl.innerHTML = Object.entries(timings)
    .map(([k, v]) => `<dt>${formatTimingLabel(k)}</dt><dd>${formatMs(v)}</dd>`)
    .join("");

  resultsPanel.classList.remove("hidden");
  errorPanel.classList.add("hidden");
  resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

errorRetry.addEventListener("click", () => {
  errorPanel.classList.add("hidden");
  document.getElementById("url").focus();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hidePanels();
  setLoading(true);

  const payload = {
    url: document.getElementById("url").value.trim(),
    vehicle: document.getElementById("vehicle").value.trim(),
  };

  if (!payload.vehicle) {
    setLoading(false);
    showError("Enter a vehicle description (e.g. 2014 Peterbilt 386).", "INVALID_VEHICLE");
    return;
  }

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      const err = data.error || {};
      showError(err.message || "Request failed", err.code);
      return;
    }

    renderResults(data);
  } catch {
    showError("Network error. Check your connection and try again.", "NETWORK_ERROR");
  } finally {
    setLoading(false);
  }
});
