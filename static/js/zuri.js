/**
 * Zuri — Bluewave Academy AI Assistant
 * Floating chat widget powered by Google Gemini
 */

(function () {
    "use strict";

    // ── Configuration ──────────────────────────────────────
    const CHAT_URL = "/zuri/chat/";
    const STORAGE_KEY = "zuri_history";
    const MAX_HISTORY = 20; // message pairs to keep in memory

    // ── State ──────────────────────────────────────────────
    let isOpen = false;
    let isThinking = false;
    let pendingImageB64 = null;
    let pendingImageName = "";
    let conversationHistory = []; // [{role, content}]

    // ── DOM refs ────────────────────────────────────────────
    const trigger = document.getElementById("zuri-trigger");
    const panel = document.getElementById("zuri-panel");
    const closeBtn = document.getElementById("zuri-close-btn");
    const messagesEl = document.getElementById("zuri-messages");
    const inputEl = document.getElementById("zuri-input");
    const sendBtn = document.getElementById("zuri-send-btn");
    const imgBtn = document.getElementById("zuri-img-btn");
    const fileInput = document.getElementById("zuri-file-input");
    const imgPreviewWrap = document.getElementById("zuri-img-preview-wrap");
    const imgPreview = document.getElementById("zuri-img-preview");
    const imgName = document.getElementById("zuri-img-name");
    const imgRemoveBtn = document.getElementById("zuri-img-remove");
    const notifDot = document.getElementById("zuri-notif");
    const rateLabel = document.querySelector(".zuri-rate-label");

    if (!trigger || !panel) return; // Guard: widget not on page

    // ── Toggle open/close ───────────────────────────────────
    function openPanel() {
        isOpen = true;
        panel.classList.add("open");
        trigger.classList.add("open");
        trigger.querySelector("#zuri-trigger-icon").className = "fa-solid fa-xmark";
        if (notifDot) notifDot.style.display = "none";
        setTimeout(() => inputEl && inputEl.focus(), 300);
        scrollToBottom();
    }

    function closePanel() {
        isOpen = false;
        panel.classList.remove("open");
        trigger.classList.remove("open");
        trigger.querySelector("#zuri-trigger-icon").className = "fa-solid fa-robot";
    }

    trigger.addEventListener("click", () => (isOpen ? closePanel() : openPanel()));
    if (closeBtn) closeBtn.addEventListener("click", closePanel);

    // Close on outside click
    document.addEventListener("click", (e) => {
        if (isOpen && !panel.contains(e.target) && !trigger.contains(e.target)) {
            closePanel();
        }
    });

    // ── Markdown → HTML (lightweight) ───────────────────────
    function markdownToHtml(text) {
        return text
            // Code blocks
            .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
                `<pre><code>${escHtml(code.trim())}</code></pre>`)
            // Inline code
            .replace(/`([^`]+)`/g, (_, c) => `<code>${escHtml(c)}</code>`)
            // Bold
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            // Italic
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            // Unordered list
            .replace(/^[-*] (.+)$/gm, "<li>$1</li>")
            .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
            // Ordered list
            .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
            // Headers
            .replace(/^### (.+)$/gm, "<strong>$1</strong>")
            .replace(/^## (.+)$/gm, "<strong>$1</strong>")
            // Line breaks → <br>
            .replace(/\n{2,}/g, "<br><br>")
            .replace(/\n/g, "<br>");
    }

    function escHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    // ── Render messages ─────────────────────────────────────
    function appendMessage(role, content, imageUrl = null, isError = false) {
        const wrap = document.createElement("div");
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
            const p = document.createElement("div");
            p.innerHTML = markdownToHtml(content);
            bubble.appendChild(p);
        }

        wrap.appendChild(avatar);
        wrap.appendChild(bubble);
        messagesEl.appendChild(wrap);
        scrollToBottom();
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
        scrollToBottom();
    }

    function hideTyping() {
        const el = document.getElementById("zuri-typing-indicator");
        if (el) el.remove();
    }

    function scrollToBottom() {
        if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // ── Image handling ───────────────────────────────────────
    imgBtn.addEventListener("click", () => fileInput.click());
    imgRemoveBtn && imgRemoveBtn.addEventListener("click", clearImage);

    fileInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 5 * 1024 * 1024) {
            alert("Image too large. Please use an image under 5 MB.");
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            pendingImageB64 = ev.target.result; // data:image/...;base64,...
            pendingImageName = file.name;
            if (imgPreview) imgPreview.src = pendingImageB64;
            if (imgName) imgName.textContent = file.name;
            if (imgPreviewWrap) imgPreviewWrap.classList.add("active");
        };
        reader.readAsDataURL(file);
        fileInput.value = "";
    });

    function clearImage() {
        pendingImageB64 = null;
        pendingImageName = "";
        if (imgPreviewWrap) imgPreviewWrap.classList.remove("active");
        if (imgPreview) imgPreview.src = "";
        if (imgName) imgName.textContent = "";
    }

    // ── Send message ─────────────────────────────────────────
    async function sendMessage() {
        if (isThinking) return;
        const text = inputEl ? inputEl.value.trim() : "";
        if (!text && !pendingImageB64) return;

        // Render user bubble
        appendMessage("user", text, pendingImageB64 ? pendingImageB64 : null);
        const sentImageB64 = pendingImageB64;
        clearImage();
        if (inputEl) inputEl.value = "";
        adjustTextarea();

        // Add to history
        if (text) {
            conversationHistory.push({ role: "user", content: text });
            if (conversationHistory.length > MAX_HISTORY * 2) {
                conversationHistory = conversationHistory.slice(-MAX_HISTORY * 2);
            }
        }

        // Show typing
        isThinking = true;
        sendBtn.disabled = true;
        showTyping();

        try {
            const payload = {
                message: text,
                history: conversationHistory.slice(-16),
            };
            if (sentImageB64) payload.image = sentImageB64;

            const res = await fetch(CHAT_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
                body: JSON.stringify(payload),
            });

            hideTyping();

            if (res.status === 429) {
                appendMessage("bot",
                    "You've reached the hourly limit of 20 messages. Zuri will be back to help you in an hour — keep studying in the meantime!",
                    null, true);
                return;
            }

            const data = await res.json();

            if (data.error && !data.reply) {
                appendMessage("bot",
                    data.message || "Something went wrong. Please try again.",
                    null, true);
                return;
            }

            const reply = data.reply || "I'm here! Could you rephrase your question?";
            appendMessage("bot", reply);

            // Store assistant turn in history
            conversationHistory.push({ role: "model", content: reply });
            if (conversationHistory.length > MAX_HISTORY * 2) {
                conversationHistory = conversationHistory.slice(-MAX_HISTORY * 2);
            }

            // Update rate label
            if (rateLabel && typeof data.remaining !== "undefined") {
                rateLabel.textContent = `${data.remaining} msgs left this hour`;
            }

        } catch (err) {
            hideTyping();
            appendMessage("bot",
                "Zuri lost connection. Please check your internet and try again.",
                null, true);
        } finally {
            isThinking = false;
            sendBtn.disabled = false;
            if (inputEl) inputEl.focus();
        }
    }

    // ── Input handlers ───────────────────────────────────────
    inputEl && inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    inputEl && inputEl.addEventListener("input", adjustTextarea);
    sendBtn && sendBtn.addEventListener("click", sendMessage);

    function adjustTextarea() {
        if (!inputEl) return;
        inputEl.style.height = "auto";
        inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + "px";
    }

    // ── CSRF helper ──────────────────────────────────────────
    function getCsrf() {
        const el = document.querySelector("[name=csrfmiddlewaretoken]");
        if (el) return el.value;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : "";
    }

    // ── Welcome message (first visit) ───────────────────────
    function showWelcome() {
        if (!messagesEl || messagesEl.children.length > 0) return;
        appendMessage(
            "bot",
            "Hi there! I'm **Zuri**, your AI assistant for Bluewave Academy.\n\nI can help you with:\n- Computer science questions & study tips\n- Info about Bluewave Academy courses & services\n- Reading and analysing images you upload\n- Anything about our founder Tinodaishe Chibi\n\nWhat can I help you with today?"
        );
    }

    // Show welcome on first open
    trigger.addEventListener("click", () => {
        setTimeout(showWelcome, 50);
    }, { once: true });

})();
