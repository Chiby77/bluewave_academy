/**
 * Zuri — Bluewave Academy AI Assistant
 * Powered by Groq · llama-3.3-70b-versatile
 * Supports: text · images · PDF documents
 */

(function () {
  "use strict";

  const CHAT_URL    = "/zuri/chat/";
  const MAX_HISTORY = 20;
  const MAX_FILE_MB = 10;

  let isOpen    = false;
  let isThinking = false;
  let conversationHistory = [];

  // Pending attachment state
  let pending = {
    b64: null,      // base64 data-URL
    name: "",
    type: null,     // "image" | "pdf"
    mime: "",
  };

  // DOM refs
  const trigger     = document.getElementById("zuri-trigger");
  const panel       = document.getElementById("zuri-panel");
  const closeBtn    = document.getElementById("zuri-close-btn");
  const messagesEl  = document.getElementById("zuri-messages");
  const inputEl     = document.getElementById("zuri-input");
  const sendBtn     = document.getElementById("zuri-send-btn");
  const attachBtn   = document.getElementById("zuri-attach-btn");
  const fileInput   = document.getElementById("zuri-file-input");
  const notifDot    = document.getElementById("zuri-notif");
  const rateLabel   = document.querySelector(".zuri-rate-label");

  // Preview rows
  const imgRow      = document.getElementById("zuri-img-row");
  const imgPrev     = document.getElementById("zuri-img-preview");
  const imgNameEl   = document.getElementById("zuri-img-name");
  const imgRemove   = document.getElementById("zuri-img-remove");

  const pdfRow      = document.getElementById("zuri-pdf-row");
  const pdfNameEl   = document.getElementById("zuri-pdf-name");
  const pdfRemove   = document.getElementById("zuri-pdf-remove");

  if (!trigger || !panel) return;

  // ── Open / Close ──────────────────────────────────────────
  function openPanel() {
    isOpen = true;
    panel.classList.add("open");
    trigger.classList.add("open");
    const icon = trigger.querySelector("#zuri-trigger-icon");
    if (icon) icon.className = "fa-solid fa-xmark";
    if (notifDot) notifDot.style.display = "none";
    setTimeout(() => inputEl && inputEl.focus(), 300);
    scrollBottom();
  }

  function closePanel() {
    isOpen = false;
    panel.classList.remove("open");
    trigger.classList.remove("open");
    const icon = trigger.querySelector("#zuri-trigger-icon");
    if (icon) icon.className = "fa-solid fa-robot";
  }

  trigger.addEventListener("click", () => isOpen ? closePanel() : openPanel());
  if (closeBtn) closeBtn.addEventListener("click", closePanel);
  document.addEventListener("click", (e) => {
    if (isOpen && !panel.contains(e.target) && !trigger.contains(e.target)) closePanel();
  });

  // ── Markdown → HTML ───────────────────────────────────────
  function md(text) {
    return text
      .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code class="lang-${lang||'text'}">${esc(code.trim())}</code></pre>`)
      .replace(/`([^`\n]+)`/g, (_, c) => `<code>${esc(c)}</code>`)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/^#{1,3} (.+)$/gm, "<strong>$1</strong>")
      .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
      .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
      .replace(/\n{2,}/g, "<br><br>")
      .replace(/\n/g, "<br>");
  }

  function esc(t) {
    return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }

  // ── Render messages ───────────────────────────────────────
  function appendMessage(role, content, opts = {}) {
    const { imageUrl, fileLabel, fileType, isError } = opts;

    const wrap = document.createElement("div");
    wrap.className = `zuri-msg ${role}${isError ? " zuri-error-bubble" : ""}`;

    const avatar = document.createElement("div");
    avatar.className = "zuri-msg-avatar";
    avatar.innerHTML = role === "bot"
      ? '<i class="fa-solid fa-robot"></i>'
      : '<i class="fa-solid fa-user"></i>';

    const bubble = document.createElement("div");
    bubble.className = "zuri-msg-bubble";

    // File context label
    if (fileLabel) {
      const fc = document.createElement("div");
      fc.className = `zuri-file-context ${fileType === "pdf" ? "pdf" : "img"}`;
      const icon = fileType === "pdf" ? "fa-file-pdf" : "fa-image";
      fc.innerHTML = `<i class="fa-solid ${icon}"></i> ${fileLabel}`;
      bubble.appendChild(fc);
    }

    // Image thumbnail
    if (imageUrl) {
      const img = document.createElement("img");
      img.src = imageUrl;
      img.className = "zuri-msg-img";
      bubble.appendChild(img);
    }

    if (content) {
      const div = document.createElement("div");
      div.innerHTML = md(content);
      bubble.appendChild(div);
    }

    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function showTyping() {
    const wrap = document.createElement("div");
    wrap.className = "zuri-msg bot zuri-typing";
    wrap.id = "zuri-typing-indicator";
    wrap.innerHTML = `
      <div class="zuri-msg-avatar"><i class="fa-solid fa-robot"></i></div>
      <div class="zuri-msg-bubble">
        <div class="zuri-dot"></div><div class="zuri-dot"></div><div class="zuri-dot"></div>
      </div>`;
    messagesEl.appendChild(wrap);
    scrollBottom();
  }

  function hideTyping() {
    const el = document.getElementById("zuri-typing-indicator");
    if (el) el.remove();
  }

  function scrollBottom() {
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── Quick chips ───────────────────────────────────────────
  function renderChips(targetBubble) {
    const chips = [
      ["fa-code",           "Explain Python lists"],
      ["fa-briefcase",      "CS career paths"],
      ["fa-graduation-cap", "Exam preparation tips"],
      ["fa-building",       "About Bluewave Academy"],
      ["fa-user-tie",       "Who is Tinodaishe?"],
      ["fa-file-pdf",       "Upload a PDF to analyse"],
    ];
    const wrap = document.createElement("div");
    wrap.className = "zuri-chips";
    chips.forEach(([icon, label]) => {
      const btn = document.createElement("button");
      btn.className = "zuri-chip";
      btn.innerHTML = `<i class="fa-solid ${icon}"></i> ${label}`;
      btn.addEventListener("click", () => {
        if (label === "Upload a PDF to analyse") {
          fileInput.click();
        } else {
          if (inputEl) inputEl.value = label;
          wrap.remove();
          sendMessage();
        }
      });
      wrap.appendChild(btn);
    });
    targetBubble.appendChild(wrap);
  }

  // ── File handling ─────────────────────────────────────────
  function isImageMime(mime) {
    return mime.startsWith("image/");
  }

  function isPdfMime(mime) {
    return mime === "application/pdf" || mime === "application/x-pdf";
  }

  if (attachBtn) attachBtn.addEventListener("click", () => fileInput && fileInput.click());
  if (imgRemove)  imgRemove.addEventListener("click", clearFile);
  if (pdfRemove)  pdfRemove.addEventListener("click", clearFile);

  if (!fileInput) return;
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      alert(`File too large. Please use a file under ${MAX_FILE_MB} MB.`);
      fileInput.value = "";
      return;
    }

    const mime = file.type || "";

    if (!isImageMime(mime) && !isPdfMime(mime)) {
      alert("Unsupported file type. Please upload an image (JPG, PNG, WebP, GIF) or a PDF.");
      fileInput.value = "";
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      const b64 = ev.target.result;
      pending = {
        b64,
        name: file.name,
        type: isPdfMime(mime) ? "pdf" : "image",
        mime,
      };

      if (pending.type === "image") {
        showImgPreview(b64, file.name);
      } else {
        showPdfPreview(file.name);
      }

      if (attachBtn) attachBtn.classList.add("has-file");
    };
    reader.readAsDataURL(file);
    fileInput.value = "";
  });

  function showImgPreview(b64, name) {
    clearPreviewRows();
    if (imgPrev)    imgPrev.src = b64;
    if (imgNameEl)  imgNameEl.textContent = name;
    if (imgRow)     imgRow.style.display = "flex";
  }

  function showPdfPreview(name) {
    clearPreviewRows();
    if (pdfNameEl)  pdfNameEl.textContent = name;
    if (pdfRow)     pdfRow.style.display = "flex";
  }

  function clearPreviewRows() {
    if (imgRow) imgRow.style.display = "none";
    if (pdfRow) pdfRow.style.display = "none";
    if (imgPrev) imgPrev.src = "";
  }

  function clearFile() {
    pending = { b64: null, name: "", type: null, mime: "" };
    clearPreviewRows();
    if (attachBtn) attachBtn.classList.remove("has-file");
  }

  // ── Send message ──────────────────────────────────────────
  async function sendMessage() {
    if (isThinking) return;

    const text = inputEl ? inputEl.value.trim() : "";
    if (!text && !pending.b64) return;

    // Show user bubble
    const msgOpts = {};
    if (pending.type === "image") {
      msgOpts.imageUrl  = pending.b64;
    } else if (pending.type === "pdf") {
      msgOpts.fileLabel = pending.name;
      msgOpts.fileType  = "pdf";
    }
    appendMessage("user", text, msgOpts);

    // Capture and clear pending
    const sentB64   = pending.b64;
    const sentType  = pending.type;
    const sentName  = pending.name;
    clearFile();
    if (inputEl) { inputEl.value = ""; adjustTA(); }

    if (text) {
      conversationHistory.push({ role: "user", content: text });
      if (conversationHistory.length > MAX_HISTORY * 2)
        conversationHistory = conversationHistory.slice(-MAX_HISTORY * 2);
    }

    isThinking = true;
    if (sendBtn) sendBtn.disabled = true;
    showTyping();

    try {
      const payload = {
        message:  text,
        history:  conversationHistory.slice(-16),
      };

      if (sentB64) {
        if (sentType === "image") {
          payload.image     = sentB64;
          payload.file_type = "image";
        } else if (sentType === "pdf") {
          payload.file      = sentB64;
          payload.file_type = "pdf";
        }
      }

      const res = await fetch(CHAT_URL, {
        method:  "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body:    JSON.stringify(payload),
      });

      hideTyping();

      if (res.status === 429) {
        appendMessage("bot",
          "You've reached the hourly limit of 20 messages. Zuri will be back to help in an hour — keep studying!",
          { isError: true });
        return;
      }

      const data = await res.json();

      if (data.error && !data.reply) {
        appendMessage("bot", data.message || "Something went wrong. Please try again.", { isError: true });
        return;
      }

      const reply = data.reply || "I'm here! Could you rephrase that?";
      appendMessage("bot", reply);

      conversationHistory.push({ role: "assistant", content: reply });
      if (conversationHistory.length > MAX_HISTORY * 2)
        conversationHistory = conversationHistory.slice(-MAX_HISTORY * 2);

      if (rateLabel && typeof data.remaining !== "undefined")
        rateLabel.textContent = `${data.remaining} msgs left this hour`;

    } catch (err) {
      hideTyping();
      appendMessage("bot", "Zuri lost connection. Please check your internet and try again.", { isError: true });
    } finally {
      isThinking = false;
      if (sendBtn) sendBtn.disabled = false;
      if (inputEl) inputEl.focus();
    }
  }

  // ── Input handlers ────────────────────────────────────────
  if (inputEl) {
    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    inputEl.addEventListener("input", adjustTA);
  }
  if (sendBtn) sendBtn.addEventListener("click", sendMessage);

  function adjustTA() {
    if (!inputEl) return;
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + "px";
  }

  function csrf() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    if (el) return el.value;
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : "";
  }

  // ── Welcome message ───────────────────────────────────────
  function showWelcome() {
    if (!messagesEl || messagesEl.children.length > 0) return;
    const wrap = appendMessage(
      "bot",
      "Hi there! I'm **Zuri**, Bluewave Academy's AI assistant — powered by Groq's advanced Llama model.\n\nI can help you with **CS questions**, **career guidance**, **exam prep**, **PDF analysis**, and everything about **Bluewave Academy**.\n\nWhat can I help you with today?"
    );
    const bubble = wrap.querySelector(".zuri-msg-bubble");
    if (bubble) renderChips(bubble);
  }

  trigger.addEventListener("click", () => setTimeout(showWelcome, 60), { once: true });

})();
