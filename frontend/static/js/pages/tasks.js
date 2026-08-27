/* AgentForge — tasks page: task cards with status + artifact URLs */
"use strict";

async function tasksPage() {
  return `
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-extrabold">Tasks</h1>
        <p class="text-slate-400 text-sm mt-1">Every agent run becomes a card — status, thread, artifacts.</p>
      </div>
      <button class="btn btn-primary btn-sm" onclick="document.getElementById('task-form-wrap').classList.toggle('hidden')">+ New task</button>
    </div>
    <div id="task-form-wrap" class="hidden card p-5 mb-6 fade-in">
      <h3 class="font-bold mb-4">Run a task</h3>
      <div class="mb-4"><label class="label">Agent</label><select id="task-agent" class="input"></select></div>
      <div class="mb-4"><label class="label">Prompt</label><textarea id="task-prompt" class="input" rows="3" placeholder="Research the top 5 AI news stories and summarize them..."></textarea></div>
      <button class="btn btn-primary btn-sm" onclick="createTask()">Queue task</button>
    </div>
    <div id="task-list" class="space-y-3"></div>`;
}

async function tasksScript() {
  try {
    const [tasks, agents] = await Promise.all([api("/tasks"), api("/agents")]);
    state.tasks = tasks; state.agents = agents;
  } catch (_) {}
  const sel = document.getElementById("task-agent");
  if (sel) {
    sel.innerHTML = state.agents.map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("");
  }
  const list = document.getElementById("task-list");
  if (!list) return;
  if (!state.tasks.length) {
    list.innerHTML = `<div class="text-center py-16 text-slate-500">
      <div class="text-4xl mb-3">📋</div>
      No tasks yet. Queue one and watch it run live.
    </div>`;
    return;
  }
  list.innerHTML = state.tasks.map((t) => `
    <div class="card p-4 fade-in">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div class="font-semibold truncate">${esc(t.prompt.slice(0, 90))}</div>
        <div class="flex items-center gap-2">${statusBadge(t.status)}</div>
      </div>
      <div class="text-xs text-slate-500 flex flex-wrap gap-x-4 gap-y-1">
        <span>📋 ${esc(t.task_type)}</span>
        <span>🧵 <code class="inline-code">${esc(t.thread_id || "—")}</code></span>
        <span>🆔 <code class="inline-code">${esc(t.id.slice(0, 8))}…</code></span>
        <span>🕐 ${fmtDate(t.created_at)}</span>
      </div>
      ${t.result ? `<div class="mt-3 text-sm text-slate-300 bg-slate-800/40 rounded-xl p-3 max-h-40 overflow-y-auto whitespace-pre-wrap">${esc(t.result.slice(0, 600))}</div>` : ""}
      ${t.error ? `<div class="mt-2 text-sm text-red-300 bg-red-500/10 rounded-xl p-3">${esc(t.error)}</div>` : ""}
      ${t.artifact_urls?.length ? `
        <div class="mt-3">
          <div class="text-xs font-semibold text-slate-400 mb-1.5">ARTIFACTS</div>
          <div class="space-y-1">${t.artifact_urls.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener" class="block text-xs text-blue-400 hover:underline truncate">📎 ${esc(u)}</a>`).join("")}</div>
        </div>` : ""}
    </div>`).join("");
}

async function createTask() {
  const agent_id = document.getElementById("task-agent").value;
  const prompt = document.getElementById("task-prompt").value.trim();
  if (!agent_id || !prompt) return toast("Pick an agent and write a prompt", "error");
  try {
    const task = await api("/tasks", { method: "POST", body: JSON.stringify({ agent_id, prompt }) });
    toast("Task queued — watch the card update live ⚡", "success");
    document.getElementById("task-form-wrap").classList.add("hidden");
    document.getElementById("task-prompt").value = "";
    state.tasks.unshift(task);
    await tasksScript();
  } catch (e) { toast(e.message, "error"); }
}
