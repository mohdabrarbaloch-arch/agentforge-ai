/* AgentForge — dashboard page */
"use strict";

async function dashboardPage() {
  const skeleton = `
    <div class="grid md:grid-cols-4 gap-4 mb-8">
      ${'<div class="skeleton h-28"></div>'.repeat(4)}
    </div>
    <div class="skeleton h-64"></div>`;
  return `
    <section class="mb-8">
      <h1 class="text-2xl sm:text-3xl font-extrabold">Hey, ${esc(state.user?.name?.split(" ")[0] || "there")} 👋</h1>
      <p class="text-slate-400 mt-1">Here's what your agents are up to today.</p>
    </section>
    <div id="stats-grid" class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">${skeleton}</div>
    <div class="grid lg:grid-cols-2 gap-6">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-bold">Recent tasks</h2>
          <a href="#/tasks" class="text-sm text-blue-400 hover:underline">View all →</a>
        </div>
        <div id="recent-tasks" class="space-y-3"><div class="skeleton h-16"></div><div class="skeleton h-16"></div></div>
      </div>
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-bold">Quick actions</h2>
        </div>
        <div class="space-y-3">
          <a href="#/agents" class="btn btn-ghost w-full justify-between"><span>🤖 Create a new agent</span><span>→</span></a>
          <a href="#/chat" class="btn btn-ghost w-full justify-between"><span>💬 Chat with an agent</span><span>→</span></a>
          <a href="#/triggers" class="btn btn-ghost w-full justify-between"><span>⏰ Schedule an automation</span><span>→</span></a>
          <a href="#/integrations" class="btn btn-ghost w-full justify-between"><span>🔌 Connect integrations</span><span>→</span></a>
        </div>
      </div>
    </div>`;
}

async function dashboardScript() {
  try {
    state.stats = await api("/dashboard/me");
    renderStats();
  } catch (e) { /* toast handled elsewhere */ }
}

function renderStats() {
  const grid = document.getElementById("stats-grid");
  if (!grid || !state.stats) return;
  const stats = state.stats;
  const cards = [
    { label: "Agents", value: stats.agent_count, icon: "🤖", to: "#/agents" },
    { label: "Tasks", value: stats.task_count, icon: "📋", to: "#/tasks" },
    { label: "Conversations", value: stats.thread_count, icon: "💬", to: "#/chat" },
    { label: "Automations", value: stats.trigger_count, icon: "⏰", to: "#/triggers" },
  ];
  grid.innerHTML = cards.map((c) => `
    <a href="${c.to}" class="card card-hover p-5 block">
      <div class="text-2xl mb-2">${c.icon}</div>
      <div class="text-3xl font-extrabold">${c.value}</div>
      <div class="text-sm text-slate-400">${c.label}</div>
    </a>`).join("");

  const recent = document.getElementById("recent-tasks");
  if (recent) {
    if (!stats.recent_tasks.length) {
      recent.innerHTML = `<div class="text-sm text-slate-500 py-6 text-center">No tasks yet — create one from <a class="text-blue-400" href="#/agents">your agent</a>.</div>`;
    } else {
      recent.innerHTML = stats.recent_tasks.map((t) => `
        <a href="#/tasks" class="block p-3 rounded-xl bg-slate-800/40 border border-slate-700/40 hover:border-blue-500/40 transition">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium truncate">${esc(t.prompt.slice(0, 60))}</span>
            ${statusBadge(t.status)}
          </div>
          <div class="text-xs text-slate-500 mt-1">${fmtDate(t.created_at)} · ${esc(t.task_type)}</div>
        </a>`).join("");
    }
  }
}
