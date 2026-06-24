/**
 * FitCheck bookmarklet — run on a product page (eBay, Amazon, etc.)
 * Captures page text in your browser and opens FitCheck (no server fetch).
 */
(function () {
  const origin = document.currentScript && document.currentScript.dataset.origin
    ? document.currentScript.dataset.origin
    : window.location.protocol + "//" + window.location.host;

  const jsonLd = [];
  document.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
    try {
      jsonLd.push(JSON.parse(s.textContent || ""));
    } catch (e) { /* ignore */ }
  });

  const payload = {
    url: location.href,
    title: document.title,
    text: (document.body && document.body.innerText ? document.body.innerText : "").slice(0, 80000),
    html: document.documentElement.outerHTML.slice(0, 120000),
    json_ld: jsonLd,
    source: "bookmarklet",
  };

  const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
  if (encoded.length > 1800000) {
    payload.html = "";
    payload.text = payload.text.slice(0, 40000);
  }

  const finalEncoded = btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
  const target = origin.replace(/\/$/, "") + "/#import=" + encodeURIComponent(finalEncoded);

  try {
    window.open(target, "_blank");
  } catch (e) {
    prompt("Copy this URL and open it in FitCheck:", target);
  }
})();
