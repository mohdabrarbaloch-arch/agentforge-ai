/* AgentForge — chat page: 1-on-1 conversations with agents */
"use strict";

async function chatPage() {
  return `
    <div class="grid lg:grid-cols-[300px_1fr] gap-6 h-[calc(100vh-140px)]">
      <div class="card p-4 flex flex-col min-h-[300px] lg:h-auto">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-bold">Conversations</h2>
          <button class="btn btn-primary btn-sm" onclick="newThread()">+ New</button>
        </div>
        <select id="chat-agent-select" class="input mb-3"></select>
        <div id="thread-list" class="flex-1 overflow-y-auto space-y-1.5"></div>
      </div>
      <div class="card flex flex-col min-h-[400px]">
        <div id="chat-header" class="px-5 py-3 border-b border-slate-800/60 flex items-center justify-between">
          <div class="font-bold">Select a conversation</div>
        </div>
        <div id="chat-messages" class="flex-1 overflow-y-auto p-5 space-y-4"></div>
        <form id="chat-form" class="p-4 border-t border-slate-800/60" onsubmit="sendChat(event)">
          <div class="flex gap-2">
            <input id="chat-input" class="input" placeholder="Ask your agent anything..." autocomplete="off" />
            <button class="btn btn-primary shrink-0" type="submit">Send ↩</button>
          </div>
          <div class="text-xs text-slate-600 mt-2">Tip: try "search the web for AI news", "generate an image of a mountain sunset", or "what time is it?"</div>
        </form>
      </div>
    </div>`;
}

async function chatScript() {
  if (!state.agents.length) {
    try { state.agents = await api("/agents"); } catch (_) {}
  }
  const select = document.getElementById("chat-agent-select");
  if (select) {
    select.innerHTML = `<option value="">Select an agent…</option>` +
      state.agents.map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("");
    const q = new URLSearchParams(window.location.hash.split("?")[1] || "");
    const preAgent = q.get("agent");
    if (preAgent && state.agents.some((a) => a.id === preAgent)) select.value = preAgent;
    select.onchange = () => { state.activeAgent = select.value; loadThreads(); };
    if (select.value) { state.activeAgent = select.value; loadThreads(); }
  }
  const list = document.getElementById("thread-list");
  if (list) {
    if (!state.threads.length) {
      list.innerHTML = `<div class="text-sm text-slate-500 text-center py-6">No conversations yet.<br>Pick an agent and start one.</div>`;
    } else {
      list.innerHTML = state.threads.map((t) => `
        <div class="p-3 rounded-xl cursor-pointer border border-slate-700/40 hover:border-blue-500/40 transition ${state.activeThread === t.id ? "bg-blue-500/10 border-blue-500/40" : "bg-slate-800/30"}"
             onclick="openThread('${esc(t.id)}')">
          <div class="text-sm font-medium truncate">${esc(t.title)}</div>
          <div class="text-xs text-slate-500 mt-0.5">${fmtDate(t.created_at)}</div>
        </div>`).join("");
    }
  }
}

async function loadThreads() {
  if (!state.activeAgent) return;
  try {
    state.threads = await api("/chat/threads");
    state.threads = state.threads.filter((t) => t.agent_id === state.activeAgent);
  } catch (_) { state.threads = []; }
  await chatScript();
}

async function newThread() {
  if (!state.activeAgent) return toast("Pick an agent first", "error");
  try {
    const t = await api("/chat/threads", { method: "POST", body: JSON.stringify({ agent_id: state.activeAgent }) });
    state.threads.unshift(t);
    state.activeThread = t.id;
    state.messages = [];
    document.getElementById("chat-messages").innerHTML = "";
    document.getElementById("chat-header").querySelector("div").textContent = "New conversation";
    await chatScript();
    document.getElementById("chat-input")?.focus();
  } catch (e) { toast(e.message, "error"); }
}

async function openThread(id) {
  state.activeThread = id;
  const thread = state.threads.find((t) => t.id === id);
  document.getElementById("chat-header").querySelector("div").textContent = thread?.title || "Conversation";
  try {
    state.messages = await api(`/chat/threads/${id}/messages`);
  } catch (_) { state.messages = []; }
  renderMessages();
  await chatScript();
}

function renderMessages() {
  const box = document.getElementById("chat-messages");
  if (!box) return;
  if (!state.messages.length) {
    box.innerHTML = `<div class="text-center text-slate-500 py-10">Say hello 👋</div>`;
    return;
  }
  box.innerHTML = state.messages.map((m) => {
    const isUser = m.role === "user";
    return `
      <div class="flex ${isUser ? "justify-end" : "justify-start"}>">
        <div class="max-w-[80%] ${isUser ? "bubble-user" : "bubble-agent"} px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          ${m.tool_name ? `<div class="text-xs text-blue-300 mb-1">🔧 ${esc(m.tool_name)}</div>` : ""}
          ${esc(m.content)}
        </div>
      </div>`;
  }).join("");
  box.scrollTop = box.scrollHeight;
}

async function sendChat(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text || !state.activeThread) {
    if (!state.activeAgent) return toast("Pick an agent first", "error");
    await newThread();
    if (!state.activeThread) return;
  }
  input.value = "";
  state.messages.push({ role: "user", content: text });
  renderMessages();

  // typing indicator
  const box = document.getElementById("chat-messages");
  const typing = document.createElement("div");
  typing.className = "flex justify-start";
  typing.innerHTML = `<div class="bubble-agent px-4 py-3 text-sm"><span class="pulse-dot inline-block w-2 h-2 rounded-full bg-blue-400 mr-1"></span> thinking…</div>`;
  box.appendChild(typing);
  box.scrollTop = box.scrollHeight;

  try {
    const data = await api(`/chat/threads/${state.activeThread}/messages`, {
      method: "POST",
      body: JSON.stringify({ message: text }),
    });
    typing.remove();
    state.messages.push({ role: "assistant", content: data.reply });
    renderMessages();
    if (data.tool_uses?.length) {
      toast("Used: " + data.tool_uses.join(", "), "info");
    }
    if (data.artifact_urls?.length) {
      data.artifact_urls.forEach((u) => toast("Artifact: " + u, "success"));
    }
  } catch (err) {
    typing.remove();
    toast(err.message, "error");
  }
}
