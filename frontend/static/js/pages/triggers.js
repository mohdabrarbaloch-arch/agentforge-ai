/* AgentForge — triggers page: cron scheduled automations */
"use strict";

async function triggersPage() {
  return `
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-extrabold">Automations</h1>
        <p class="text-slate-400 text-sm mt-1">Cron-based triggers that put your agents on a schedule.</p>
      </div>
      <button class="btn btn-primary btn-sm" onclick="document.getElementById('trigger-form-wrap').classList.toggle('hidden')">+ New trigger</button>
    </div>
    <div id="trigger-form-wrap" class="hidden card p-5 mb-6 fade-in">
      <h3 class="font-bold mb-4">Schedule an automation</h3>
      <div class="grid md:grid-cols-2 gap-4">
        <div><label class="label">Name</label><input id="tr-name" class="input" placeholder="Morning briefing" /></div>
        <div><label class="label">Cron expression (5 fields)</label><input id="tr-cron" class="input" placeholder="0 9 * * *" value="0 9 * * *" /></div>
      </div>
      <div class="mt-4 grid md:grid-cols-2 gap-4">
        <div><label class="label">Agent</label><select id="tr-agent" class="input"></select></div>
        <div><label class="label">Timezone</label><input id="tr-tz" class="input" value="Asia/Karachi" /></div>
      </div>
      <div class="mt-4"><label class="label">Prompt (what should the agent do?)</label><textarea id="tr-prompt" class="input" rows="3" placeholder="Summarize the latest tech news and save it as a report..."></textarea></div>
      <div class="text-xs text-slate-500 mt-2">Cron examples: <code class="inline-code">0 9 * * *</code> daily 9am · <code class="inline-code">0 */6 * * *</code> every 6h · <code class="inline-code">0 8 * * 1</code> Mondays 8am</div>
      <div class="mt-5"><button class="btn btn-primary btn-sm" onclick="createTrigger()">Create trigger</button></div>
    </div>
    <div id="trigger-list" class="space-y-3"></div>`;
}

async function triggersScript() {
  try {
    const [triggers, agents] = await Promise.all([api("/triggers"), api("/agents")]);
    state.triggers = triggers; state.agents = agents;
  } catch (_) {}
  const sel = document.getElementById("tr-agent");
  if (sel) {
    sel.innerHTML = state.agents.map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("");
  }
  const list = document.getElementById("trigger-list");
  if (!list) return;
  if (!state.triggers.length) {
    list.innerHTML = `<div class="text-center py-16 text-slate-500">
      <div class="text-4xl mb-3">⏰</div>
      No automations yet. Schedule your first one — "every morning at 9, summarize the news".
    </div>`;
    return;
  }
  list.innerHTML = state.triggers.map((t) => `
    <div class="card p-4 flex flex-wrap items-center justify-between gap-3">
      <div class="min-w-0">
        <div class="font-semibold">${esc(t.name)}</div>
        <div class="text-xs text-slate-500 mt-0.5">
          <code class="inline-code">${esc(t.cron_expression)}</code> · ${esc(t.timezone)} · next run: ${fmtDate(t.next_run_at)}
        </div>
        <div class="text-xs text-slate-500 mt-1">${esc(t.prompt.slice(0, 90))}</div>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button class="btn btn-sm ${t.enabled ? "btn-ghost" : "btn-primary"}" onclick="toggleTrigger('${esc(t.id)}')">${t.enabled ? "Pause" : "Resume"}</button>
        <button class="btn btn-danger btn-sm" onclick="deleteTrigger('${esc(t.id)}')">Delete</button>
      </div>
    </div>`).join("");
}

async function createTrigger() {
  const payload = {
    name: document.getElementById("tr-name").value.trim(),
    cron_expression: document.getElementById("tr-cron").value.trim(),
    agent_id: document.getElementById("tr-agent").value || null,
    prompt: document.getElementById("tr-prompt").value.trim(),
    timezone: document.getElementById("tr-tz").value.trim() || "Asia/Karachi",
  };
  if (!payload.name || !payload.prompt) return toast("Name and prompt are required", "error");
  try {
    await api("/triggers", { method: "POST", body: JSON.stringify(payload) });
    toast("Automation scheduled! ⏰", "success");
    document.getElementById("trigger-form-wrap").classList.add("hidden");
    await triggersScript();
  } catch (e) { toast(e.message, "error"); }
}

async function toggleTrigger(id) {
  const t = state.triggers.find((x) => x.id === id);
  try {
    await api(`/triggers/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !t.enabled }) });
    await triggersScript();
  } catch (e) { toast(e.message, "error"); }
}

async function deleteTrigger(id) {
  if (!confirm("Delete this automation?")) return;
  try {
    await api(`/triggers/${id}`, { method: "DELETE" });
    toast("Automation deleted", "success");
    await triggersScript();
  } catch (e) { toast(e.message, "error"); }
}
