/* AgentForge — agents page: create, configure, delete */
"use strict";

async function agentsPage() {
  return `
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-extrabold">Your agents</h1>
        <p class="text-slate-400 text-sm mt-1">Create agents, give them tools, put them to work.</p>
      </div>
      <button class="btn btn-primary btn-sm" onclick="document.getElementById('agent-form-wrap').classList.toggle('hidden')">+ New agent</button>
    </div>
    <div id="agent-form-wrap" class="hidden card p-5 mb-6 fade-in">
      <h3 class="font-bold mb-4">Create an agent</h3>
      <div class="grid md:grid-cols-2 gap-4">
        <div><label class="label">Name</label><input id="ag-name" class="input" placeholder="Content Creator" /></div>
        <div><label class="label">Model</label>
          <select id="ag-model" class="input">
            <option value="gpt-4o-mini">gpt-4o-mini (fast, cheap)</option>
            <option value="gpt-4o">gpt-4o (smart)</option>
            <option value="claude-3-5-sonnet-latest">claude-3-5-sonnet</option>
          </select>
        </div>
      </div>
      <div class="mt-4"><label class="label">Description</label><input id="ag-desc" class="input" placeholder="What is this agent for?" /></div>
      <div class="mt-4"><label class="label">System prompt</label><textarea id="ag-prompt" class="input" rows="3" placeholder="You are a helpful assistant that..."></textarea></div>
      <div class="mt-4">
        <label class="label">Tools (click to toggle)</label>
        <div id="ag-tools" class="flex flex-wrap gap-2"></div>
      </div>
      <div class="mt-5 flex gap-2">
        <button class="btn btn-primary btn-sm" onclick="createAgent()">Create agent</button>
        <button class="btn btn-ghost btn-sm" onclick="document.getElementById('agent-form-wrap').classList.add('hidden')">Cancel</button>
      </div>
    </div>
    <div id="agent-list" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>`;
}

async function agentsScript() {
  const [agents, tools] = await Promise.all([api("/agents"), api("/agents/tools")]);
  state.agents = agents; state.tools = tools;

  // tool chips in the create form
  const chipWrap = document.getElementById("ag-tools");
  if (chipWrap) {
    const selected = new Set(["web_search", "get_time"]);
    chipWrap.innerHTML = tools.map((t) => `
      <span class="chip ${selected.has(t.name) ? "active" : ""}" data-tool="${t.name}" onclick="this.classList.toggle('active')">${esc(t.name)}</span>`).join("");
    window.__selectedTools = selected;
  }

  const list = document.getElementById("agent-list");
  if (!list) return;
  if (!agents.length) {
    list.innerHTML = `<div class="col-span-full text-center py-16 text-slate-500">
      <div class="text-4xl mb-3">🤖</div>
      No agents yet. Create your first one — give it a personality and some tools.
    </div>`;
    return;
  }
  list.innerHTML = agents.map((a) => `
    <div class="card card-hover p-5 flex flex-col">
      <div class="flex items-start justify-between mb-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/30 to-purple-600/30 flex items-center justify-center text-lg">🤖</div>
        <span class="text-xs text-slate-500">${esc(a.model)}</span>
      </div>
      <h3 class="font-bold text-lg">${esc(a.name)}</h3>
      <p class="text-sm text-slate-400 mt-1 flex-1">${esc(a.description || "No description")}</p>
      <div class="flex flex-wrap gap-1.5 mt-3">
        ${(a.enabled_tools || []).slice(0, 5).map((t) => `<span class="badge bg-blue-500/10 text-blue-300 border border-blue-500/20">${esc(t)}</span>`).join("")}
        ${(a.enabled_tools || []).length > 5 ? `<span class="badge bg-slate-500/10 text-slate-400 border border-slate-500/20">+${a.enabled_tools.length - 5}</span>` : ""}
      </div>
      <div class="flex gap-2 mt-4 pt-4 border-t border-slate-800/60">
        <a href="#/chat?agent=${esc(a.id)}" class="btn btn-primary btn-sm flex-1">Chat</a>
        <button class="btn btn-danger btn-sm" onclick="deleteAgent('${esc(a.id)}')">Delete</button>
      </div>
    </div>`).join("");
}

async function createAgent() {
  const selected = window.__selectedTools ? [...window.__selectedTools].filter((t) => {
    const chip = document.querySelector(`[data-tool="${t}"]`);
    return chip && chip.classList.contains("active");
  }) : [];
  const payload = {
    name: document.getElementById("ag-name").value.trim(),
    description: document.getElementById("ag-desc").value.trim(),
    system_prompt: document.getElementById("ag-prompt").value.trim(),
    model: document.getElementById("ag-model").value,
    enabled_tools: selected,
  };
  if (!payload.name || !payload.system_prompt) return toast("Name and system prompt are required", "error");
  try {
    await api("/agents", { method: "POST", body: JSON.stringify(payload) });
    toast("Agent created! 🎉", "success");
    document.getElementById("agent-form-wrap").classList.add("hidden");
    await agentsScript();
  } catch (e) { toast(e.message, "error"); }
}

async function deleteAgent(id) {
  if (!confirm("Delete this agent? Its conversations go too.")) return;
  try {
    await api(`/agents/${id}`, { method: "DELETE" });
    toast("Agent deleted", "success");
    await agentsScript();
  } catch (e) { toast(e.message, "error"); }
}
