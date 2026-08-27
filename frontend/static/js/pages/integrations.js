/* AgentForge — integrations page: connect services + API keys */
"use strict";

const SERVICES = [
  { id: "gmail", name: "Gmail", icon: "✉️", desc: "Send and read emails" },
  { id: "slack", name: "Slack", icon: "💬", desc: "Post messages to channels" },
  { id: "notion", name: "Notion", icon: "📝", desc: "Create pages and notes" },
  { id: "github", name: "GitHub", icon: "🐙", desc: "Issues, repos, actions" },
  { id: "stripe", name: "Stripe", icon: "💳", desc: "Payments & billing" },
];

async function integrationsPage() {
  return `
    <h1 class="text-2xl font-extrabold mb-1">Integrations</h1>
    <p class="text-slate-400 text-sm mb-6">Connect the services your agents can act on.</p>
    <div id="svc-grid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8"></div>
    <div class="card p-5">
      <h2 class="font-bold mb-1">API keys</h2>
      <p class="text-sm text-slate-400 mb-4">Programmatic access — send Bearer <code class="inline-code">agf_…</code> to call the API as your user.</p>
      <div class="flex gap-2 mb-4">
        <input id="key-name" class="input max-w-xs" placeholder="My script" />
        <button class="btn btn-primary btn-sm" onclick="createApiKey()">Generate key</button>
      </div>
      <div id="key-list" class="space-y-2"></div>
    </div>`;
}

async function integrationsScript() {
  try {
    const [integrations, keys] = await Promise.all([api("/integrations"), api("/integrations/api-keys")]);
    state.integrations = integrations; state.apiKeys = keys;
  } catch (_) {}

  const grid = document.getElementById("svc-grid");
  if (grid) {
    grid.innerHTML = SERVICES.map((s) => {
      const conn = state.integrations.find((i) => i.service === s.id);
      const connected = conn && conn.status === "connected";
      return `
        <div class="card card-hover p-5">
          <div class="flex items-center justify-between mb-3">
            <span class="text-2xl">${s.icon}</span>
            <span class="badge border ${connected ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" : "bg-slate-500/10 text-slate-400 border-slate-500/25"}">${connected ? "● Connected" : "○ Disconnected"}</span>
          </div>
          <h3 class="font-bold">${s.name}</h3>
          <p class="text-sm text-slate-400 mt-1 mb-4">${s.desc}</p>
          <button class="btn ${connected ? "btn-danger" : "btn-ghost"} btn-sm w-full" onclick="${connected ? `disconnectService('${conn.id}')` : `connectService('${s.id}')`}">
            ${connected ? "Disconnect" : "Connect"}
          </button>
        </div>`;
    }).join("");
  }

  const keys = document.getElementById("key-list");
  if (keys) {
    if (!state.apiKeys.length) {
      keys.innerHTML = `<div class="text-sm text-slate-500">No API keys yet.</div>`;
    } else {
      keys.innerHTML = state.apiKeys.map((k) => `
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-slate-700/40">
          <div>
            <div class="text-sm font-medium">${esc(k.name)}</div>
            <div class="text-xs text-slate-500 mt-0.5">${esc(k.prefix)}… · created ${fmtDate(k.created_at)} · last used ${fmtDate(k.last_used_at)}</div>
          </div>
          <button class="btn btn-danger btn-sm" onclick="revokeKey('${esc(k.id)}')">Revoke</button>
        </div>`).join("");
    }
  }
}

async function connectService(service) {
  try {
    await api("/integrations/connect", { method: "POST", body: JSON.stringify({ service }) });
    toast(`${service} connected! Agents can now use it (demo mode: simulated actions).`, "success");
    await integrationsScript();
  } catch (e) { toast(e.message, "error"); }
}

async function disconnectService(id) {
  if (!confirm("Disconnect this integration?")) return;
  try {
    await api(`/integrations/${id}`, { method: "DELETE" });
    toast("Integration disconnected", "success");
    await integrationsScript();
  } catch (e) { toast(e.message, "error"); }
}

async function createApiKey() {
  const name = document.getElementById("key-name").value.trim();
  if (!name) return toast("Give the key a name", "error");
  try {
    const k = await api("/integrations/api-keys", { method: "POST", body: JSON.stringify({ name }) });
    await navigator.clipboard?.writeText(k.key).catch(() => {});
    toast(`Key created: ${k.key.slice(0, 14)}… (copied to clipboard) — shown only once!`, "success");
    await integrationsScript();
  } catch (e) { toast(e.message, "error"); }
}

async function revokeKey(id) {
  if (!confirm("Revoke this API key?")) return;
  try {
    await api(`/integrations/api-keys/${id}`, { method: "DELETE" });
    toast("Key revoked", "success");
    await integrationsScript();
  } catch (e) { toast(e.message, "error"); }
}
