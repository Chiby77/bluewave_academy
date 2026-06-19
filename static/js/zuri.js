/**
 * Zuri — Bluewave Academy AI Assistant
 * Powered by Groq · llama-3.3-70b-versatile
 */

(function () {
  "use strict";

  const CHAT_URL   = "/zuri/chat/";
  const MAX_HISTORY = 20;

  let isOpen    = false;
  let isThinking = false;
  let pendingImageB64  = null;
  let pendingImageName = "";
  let conversationHistory = []; // [{role, content}]

  const trigger       = document.getElementById("zuri-trigger");
  const panel         = document.getElementById("zuri-panel");
  const closeBtn      = document.getElementById("zuri-close-btn");
  const messagesEl    = document.getElementById("zuri-messages");
  const inputEl       = document.getElementById("zuri-input");
  const sendBtn       = document.getElementById("zuri-send-btn");
  const imgBtn        = document.getElementById("zuri-img-btn");
  const fileInput     = document.getElementById("zuri-file-input");
  const imgPrevWrap   = document.getElementById("zuri-img-preview-wrap");
  const imgPrev       = document.getElementById("zuri-img-preview");
  const imgNameEl     = document.getElementById("zuri-img-name");
  const imgRemoveBtn  = document.getElementById("zuri-img-remove");
  const notifDot      = document.getElementById("zuri-notif");
  const rateLabel     = document.querySelector(".zuri-rate-label");

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
        `<pre><code>${esc(code.trim())}</code></pre>`)
      .replace(/`([^`]+)`/g, (_, c) => `<code>${esc(c)}</code>`)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
      .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
      .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
      .replace(/^### (.+)$/gm, "<strong>$1</strong>")
      .replace(/^## (.+)$/gm,  "<strong>$1</strong>")
      .replace(/\n{2,}/g, "<br><br>")
      .replace(/\n/g, "<br>");
  }

  function esc(t) {
    return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }

  // ── Render ────────────────────────────────────────────────
  function appendMessage(role, content, imageUrl, isError) {
    const wrap   = document.createElement("div");
    wrap.className = `zuri-msg ${role}${isError ? " zuri-error-bubble" : ""}`;

    const avatar = document.createElement("div");
    avatar.className = "zuri-msg-avatar";
    avatar.innerHTML = role === "bot"
      ? '<i class="fa-solid fa-robot"></i>'
      : '<i class="fa-solid fa-user"></i>';

    const bubble = document.createElement("div");
    bubble.className = "zuri-msg-bubble";

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
        <div class="zuri-dot"></div>
        <div class="zuri-dot"></div>
        <div class="zuri-dot"></div>
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
      ["fa-code",        "Python help"],
      ["fa-graduation-cap", "Exam tips"],
      ["fa-building",    "About Bluewave"],
      ["fa-user",        "Who is Tinodaishe?"],
    ];
    const wrap = document.createElement("div");
    wrap.className = "zuri-chips";
    chips.forEach(([icon, label]) => {
      const btn = document.createElement("button");
      btn.className = "zuri-chip";
      btn.innerHTML = `<i class="fa-solid ${icon}"></i> ${label}`;
      btn.addEventListener("click", () => {
        if (inputEl) inputEl.value = label;
        wrap.remove();
        sendMessage();
      });
      wrap.appendChild(btn);
    });
    targetBubble.appendChild(wrap);
  }

  // ── Image handling ────────────────────────────────────────
  if (imgBtn) imgBtn.addEventListener("click", () => fileInput.click());
  if (imgRemoveBtn) imgRemoveBtn.addEventListener("click", clearImage);

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      alert("Image too large. Please use an image under 5 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      pendingImageB64  = ev.target.result;
      pendingImageName = file.name;
      if (imgPrev) imgPrev.src = pendingImageB64;
      if (imgNameEl) imgNameEl.textContent = file.name;
      if (imgPrevWrap) imgPrevWrap.classList.add("active");
    };
    reader.readAsDataURL(file);
    fileInput.value = "";
  });

  function clearImage() {
    pendingImageB64 = null; pendingImageName = "";
    if (imgPrevWrap) imgPrevWrap.classList.remove("active");
    if (imgPrev)    imgPrev.src = "";
    if (imgNameEl)  imgNameEl.textContent = "";
  }

  // ── Send ──────────────────────────────────────────────────
  async function sendMessage() {
    if (isThinking) return;
    const text = inputEl ? inputEl.value.trim() : "";
    if (!text && !pendingImageB64) return;

    appendMessage("user", text, pendingImageB64 || null);
    const sentImage = pendingImageB64;
    clearImage();
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
      const payload = { message: text, history: conversationHistory.slice(-16) };
      if (sentImage) payload.image = sentImage;

      const res = await fetch(CHAT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify(payload),
      });

      hideTyping();

      if (res.status === 429) {
        appendMessage("bot",
          "You've reached the hourly limit of 20 messages. Zuri will be back to help in an hour — keep studying!",
          null, true);
        return;
      }

      const data = await res.json();
      if (data.error && !data.reply) {
        appendMessage("bot", data.message || "Something went wrong. Please try again.", null, true);
        return;
      }

      const reply = data.reply || "I'm here! Could you rephrase that?";
      appendMessage("bot", reply);

      // Groq uses "assistant" role
      conversationHistory.push({ role: "assistant", content: reply });
      if (conversationHistory.length > MAX_HISTORY * 2)
        conversationHistory = conversationHistory.slice(-MAX_HISTORY * 2);

      if (rateLabel && typeof data.remaining !== "undefined")
        rateLabel.textContent = `${data.remaining} msgs left this hour`;

    } catch (err) {
      hideTyping();
      appendMessage("bot", "Zuri lost connection. Please check your internet and try again.", null, true);
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

  // ── Welcome ───────────────────────────────────────────────
  function showWelcome() {
    if (!messagesEl || messagesEl.children.length > 0) return;
    const wrap = appendMessage(
      "bot",
      "Hi there! I'm **Zuri**, Bluewave Academy's AI assistant — powered by Groq's advanced Llama model.\n\nI can help you with computer science questions, exam prep, study resources, and anything about Bluewave Academy.\n\nWhat can I help you with today?"
    );
    const bubble = wrap.querySelector(".zuri-msg-bubble");
    if (bubble) renderChips(bubble);
  }

  trigger.addEventListener("click", () => {
    setTimeout(showWelcome, 60);
  }, { once: true });

})();
