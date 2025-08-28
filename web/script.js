// web/script.js

(function () {
  const apiBase = location.origin;

  // Elements from the page
  const form = document.getElementById('issueForm');        // the Generate QR form
  const qrBox = document.getElementById('qrBox');            // where the QR image appears
  const printBtn = document.getElementById('btnPrint');      // Print button (if present)
  const msg = document.getElementById('msg');                // small error/info text
  const printInfo = document.getElementById('printInfo');    // our new info area

  // If your page uses the verify/payload UI from earlier, these may exist:
  const payloadInput = document.getElementById('payload');
  const btnVerify = document.getElementById('btnVerify');
  const verifyMsg = document.getElementById('verifyMsg');

  if (!form) {
    console.warn("issueForm not found. Make sure your index.html has a <form id=\"issueForm\">…</form>.");
    return;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();               // prevent default GET
    msg && (msg.textContent = '');
    verifyMsg && (verifyMsg.textContent = '');
    printInfo && (printInfo.innerHTML = '');
    qrBox.innerHTML = '<div class="muted">Generating...</div>';
    if (printBtn) printBtn.disabled = true;
    if (btnVerify) btnVerify.disabled = true;

    const fd = new FormData(form);

    try {
      const res = await fetch(apiBase + "/qr/issue", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));

      if (!res.ok || !data.ok) {
        msg && (msg.textContent = 'Error: ' + (data.error || (res.status + ' ' + res.statusText)));
        qrBox.innerHTML = '<div class="muted">No QR</div>';
        return;
      }

      // Show QR image (add cache-buster so it always refreshes)
      const token = data.token;
      const img = document.createElement('img');
      img.src = apiBase + "/qr/png/" + token + "?t=" + Date.now();
      img.alt = 'QR Code';
      qrBox.innerHTML = '';
      qrBox.appendChild(img);

      // Build payload automatically (if your page has that UI)
      if (payloadInput) {
        payloadInput.value = "BenimGiriş|" + token;
        if (btnVerify) btnVerify.disabled = false;
      }

      // Show user info list from print_info
      if (printInfo && data.print_info) {
        let html = '<h4 style="margin:8px 0 4px">User Info</h4><ul style="margin:0;padding-left:18px;">';
        for (const [k, v] of Object.entries(data.print_info)) {
          html += <li><b>${k}:</b> ${v ?? ''}</li>;
        }
        html += '</ul>';
        printInfo.innerHTML = html;
      }

      // Enable Print button (if present)
      if (printBtn) printBtn.disabled = false;

    } catch (err) {
      console.error(err);
      msg && (msg.textContent = 'Request failed. Is the server running?');
      qrBox.innerHTML = '<div class="muted">No QR</div>';
    }
  });
})();