const form = document.getElementById("scan-form");
const submitBtn = document.getElementById("submit-btn");
const spinner = document.getElementById("spinner");
const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");
const errorCode = document.getElementById("error-code");
const resultsPanel = document.getElementById("results");

function setLoading(loading) {
  submitBtn.disabled = loading;
  spinner.classList.toggle("hidden", !loading);
  submitBtn.querySelector(".btn-text").textContent = loading
    ? "Analyzing..."
    : "Check Compatibility";
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
}

function formatMs(ms) {
  return `${Math.round(ms)} ms`;
}

function renderResults(data) {
  const { product, compatibility, timings } = data;
  const badge = document.getElementById("compatibility-badge");
  const summary = document.getElementById("summary");

  if (compatibility.compatible === true) {
    badge.textContent = `Compatible (${compatibility.confidence} confidence)`;
    badge.className = "badge compatible";
  } else if (compatibility.compatible === false) {
    badge.textContent = `Not Compatible (${compatibility.confidence} confidence)`;
    badge.className = "badge incompatible";
  } else {
    badge.textContent = `Unknown (${compatibility.confidence} confidence)`;
    badge.className = "badge unknown";
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
    .map(([k, v]) => `<dt>${k.replace(/_/g, " ")}</dt><dd>${formatMs(v)}</dd>`)
    .join("");

  resultsPanel.classList.remove("hidden");
  errorPanel.classList.add("hidden");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hidePanels();
  setLoading(true);

  const payload = {
    url: document.getElementById("url").value.trim(),
    vehicle: document.getElementById("vehicle").value.trim(),
  };

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
  } catch (err) {
    showError("Network error. Please try again.", "NETWORK_ERROR");
  } finally {
    setLoading(false);
  }
});
