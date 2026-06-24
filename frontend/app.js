const form = document.getElementById("scan-form");
const submitBtn = document.getElementById("submit-btn");
const spinner = document.getElementById("spinner");
const loadingStatus = document.getElementById("loading-status");
const loadingLabel = document.getElementById("loading-label");
const errorPanel = document.getElementById("error-panel");
const errorMessage = document.getElementById("error-message");
const errorCode = document.getElementById("error-code");
const errorRetry = document.getElementById("error-retry");
const errorSuggestions = document.getElementById("error-suggestions");
const errorDebug = document.getElementById("error-debug");
const errorDebugBody = document.getElementById("error-debug-body");
const resultsPanel = document.getElementById("results");
const importBanner = document.getElementById("import-banner");

let currentMode = "url";
let importedPageContent = null;

const LOADING_STAGES_URL = [
  "Validating URL…",
  "Fetching product page…",
  "Extracting fitment data…",
  "Analyzing compatibility…",
];

const LOADING_STAGES_CLIENT = [
  "Using page from your browser…",
  "Extracting fitment data…",
  "Analyzing compatibility…",
];

let loadingTimer = null;

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll(".mode-tab").forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.getElementById("panel-url").classList.toggle("hidden", mode !== "url");
  document.getElementById("panel-paste").classList.toggle("hidden", mode !== "paste");
  document.getElementById("panel-bookmarklet").classList.toggle("hidden", mode !== "bookmarklet");
}

document.querySelectorAll(".mode-tab").forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

function buildBookmarkletCode() {
  const origin = window.location.origin;
  return (
    "javascript:(function(){" +
    `var o=${JSON.stringify(origin)};` +
    "var j=[];document.querySelectorAll('script[type=\"application/ld+json\"]').forEach(function(s){" +
    "try{j.push(JSON.parse(s.textContent||''));}catch(e){}});" +
    "var p={url:location.href,title:document.title," +
    "text:(document.body&&document.body.innerText||'').slice(0,80000)," +
    "html:document.documentElement.outerHTML.slice(0,120000)," +
    "json_ld:j,source:'bookmarklet'};" +
    "var e=btoa(unescape(encodeURIComponent(JSON.stringify(p))));" +
    "window.open(o+'/#import='+encodeURIComponent(e),'_blank');" +
    "})();"
  );
}

function initBookmarklet() {
  const link = document.getElementById("bookmarklet-link");
  const code = buildBookmarkletCode();
  link.href = code;
  document.getElementById("copy-bookmarklet").addEventListener("click", async () => {
    const raw = code.replace(/^javascript:/, "");
    try {
      await navigator.clipboard.writeText(`javascript:${raw}`);
      document.getElementById("copy-bookmarklet").textContent = "Copied!";
      setTimeout(() => {
        document.getElementById("copy-bookmarklet").textContent = "Copy bookmarklet code";
      }, 2000);
    } catch {
      prompt("Copy this bookmarklet URL:", code);
    }
  });
}

function decodeImportHash() {
  const hash = location.hash;
  if (!hash.startsWith("#import=")) return;
  try {
    const encoded = decodeURIComponent(hash.slice("#import=".length));
    const json = decodeURIComponent(escape(atob(encoded)));
    importedPageContent = JSON.parse(json);
    history.replaceState(null, "", location.pathname + location.search);
    setMode("paste");
    if (importedPageContent.url) {
      document.getElementById("paste-url").value = importedPageContent.url;
    }
    if (importedPageContent.text) {
      document.getElementById("paste-content").value = importedPageContent.text.slice(0, 50000);
    }
    importBanner.classList.remove("hidden");
    document.getElementById("vehicle").focus();
  } catch {
    showError("Could not read captured page data from bookmarklet.", "IMPORT_ERROR");
  }
}

function setLoading(loading, clientMode = false) {
  submitBtn.disabled = loading;
  spinner.classList.toggle("hidden", !loading);
  loadingStatus.classList.toggle("hidden", !loading);

  const stages = clientMode ? LOADING_STAGES_CLIENT : LOADING_STAGES_URL;

  if (loading) {
    let stage = 0;
    loadingLabel.textContent = stages[0];
    loadingTimer = window.setInterval(() => {
      stage = Math.min(stage + 1, stages.length - 1);
      loadingLabel.textContent = stages[stage];
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

function showError(message, code, details = {}) {
  errorMessage.textContent = message;
  errorCode.textContent = code ? `Code: ${code}` : "";

  const suggestions = details.suggestions || [];
  if (details.hint && !suggestions.length) {
    suggestions.push(details.hint);
  }
  errorSuggestions.innerHTML = "";
  if (suggestions.length) {
    errorSuggestions.classList.remove("hidden");
    for (const s of suggestions) {
      errorSuggestions.innerHTML += `<li>${escapeHtml(s)}</li>`;
    }
  } else {
    errorSuggestions.classList.add("hidden");
  }

  const fetchTrace = details.fetch || details.debug || null;
  if (fetchTrace) {
    errorDebug.classList.remove("hidden");
    errorDebugBody.textContent = JSON.stringify(fetchTrace, null, 2);
  } else if (details.status_code || details.final_url || details.bot_protection) {
    errorDebug.classList.remove("hidden");
    errorDebugBody.textContent = JSON.stringify(
      {
        status_code: details.status_code,
        final_url: details.final_url,
        bot_protection: details.bot_protection,
      },
      null,
      2,
    );
  } else {
    errorDebug.classList.add("hidden");
    errorDebugBody.textContent = "";
  }

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

function buildPageContentPayload() {
  if (importedPageContent) {
    return { ...importedPageContent };
  }
  const pasteText = document.getElementById("paste-content").value.trim();
  const pasteUrl = document.getElementById("paste-url").value.trim();
  if (!pasteText) return null;
  return {
    url: pasteUrl || null,
    text: pasteText,
    source: "paste",
  };
}

errorRetry.addEventListener("click", () => {
  errorPanel.classList.add("hidden");
  if (currentMode === "url") {
    document.getElementById("url").focus();
  } else {
    document.getElementById("vehicle").focus();
  }
});

initBookmarklet();
decodeImportHash();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hidePanels();
  importBanner.classList.add("hidden");

  const vehicle = document.getElementById("vehicle").value.trim();

  if (!vehicle) {
    showError("Enter a vehicle description (e.g. 2014 Peterbilt 386).", "INVALID_VEHICLE");
    return;
  }

  let payload;
  let clientMode = false;

  if (currentMode === "paste" || importedPageContent) {
    const pageContent = buildPageContentPayload();
    if (!pageContent || !(pageContent.text || pageContent.html)) {
      showError("Paste page text from the product listing, or use the bookmarklet.", "MISSING_CONTENT");
      return;
    }
    payload = { vehicle, page_content: pageContent };
    clientMode = true;
    importedPageContent = null;
  } else if (currentMode === "bookmarklet") {
    showError(
      "Use the bookmarklet on the product page first — it opens FitCheck with the page captured.",
      "BOOKMARKLET_REQUIRED",
      {
        suggestions: [
          "Drag “Capture to FitCheck” to your bookmarks bar.",
          "Open the eBay/Amazon listing, click the bookmark, then enter your vehicle here.",
        ],
      },
    );
    return;
  } else {
    const url = document.getElementById("url").value.trim();
    if (!url) {
      showError("Enter a product URL or switch to Paste / Bookmarklet mode.", "MISSING_URL");
      return;
    }
    payload = { url, vehicle };
  }

  setLoading(true, clientMode);

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      const err = data.error || {};
      showError(err.message || "Request failed", err.code, err.details || {});
      return;
    }

    renderResults(data);
  } catch {
    showError("Network error. Check your connection and try again.", "NETWORK_ERROR");
  } finally {
    setLoading(false, clientMode);
  }
});
