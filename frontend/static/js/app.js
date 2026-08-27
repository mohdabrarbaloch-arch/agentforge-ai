/* AgentForge SPA — core: state, api, router, ui helpers */
"use strict";

const API = "/api";
const state = {
  token: localStorage.getItem("agf_token") || "",
  user: null,
  route: window.location.hash || "#/",
  agents: [],
  threads: [],
  messages: [],
  tasks: [],
  triggers: [],
  integrations: [],
  apiKeys: [],
  tools: [],
  activeAgent: null,
  activeThread: null,
  stats: null,
  ws: null,
};

/* ---------------- API ---------------- */
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (state.token) headers["Authorization"] = `Bearer ${state.token}`;
  const res = await fetch(API + path, { ...opts, headers });
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Session expired — please log in again.");
  }
  if (!res.ok) {
    const detail = data && (data.detail || (Array.isArray(data) && data[0]?.msg));
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

/* ---------------- UI helpers ---------------- */
function toast(message, type = "info") {
  const wrap = document.getElementById("toast-wrap");
  const colors = { info: "border-blue-500/40 text-blue-200", success: "border-emerald-500/40 text-emerald-200", error: "border-red-500/40 text-red-200" };
  const el = document.createElement("div");
  el.className = `glass px-4 py-3 rounded-xl text-sm font-medium fade-in ${colors[type] || colors.info}`;
  el.textContent = message;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity .3s"; setTimeout(() => el.remove(), 350); }, 3600);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-PK", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function statusBadge(status) {
  const map = {
    queued: ["bg-amber-500/15 text-amber-300 border-amber-500/30", "⏳"],
    running: ["bg-blue-500/15 text-blue-300 border-blue-500/30", "🔄"],
    succeeded: ["bg-emerald-500/15 text-emerald-300 border-emerald-500/30", "✅"],
    failed: ["bg-red-500/15 text-red-300 border-red-500/30", "❌"],
    cancelled: ["bg-slate-500/15 text-slate-300 border-slate-500/30", "⏹️"],
  };
  const [cls, icon] = map[status] || [map.queued[0], "•"];
  return `<span class="badge border ${cls}">${icon} ${esc(status)}</span>`;
}

/* ---------------- Router ---------------- */
async function router() {
  const path = window.location.hash || "#/";
  state.route = path;
  const app = document.getElementById("app");

  if (path.startsWith("#/login")) return renderAuth(app, "login");
  if (path.startsWith("#/register")) return renderAuth(app, "register");

  if (!state.token) { window.location.hash = "#/login"; return; }

  if (!state.user) {
    try { state.user = await api("/auth/me"); } catch (_) { logout(); return; }
  }

  const body = `
    <nav class="sticky top-0 z-40 glass border-b border-slate-800/60">
      <div class="max-w-7xl mx-auto px-4 flex items-center justify-between h-16">
        <a href="#/" class="flex items-center gap-2 font-extrabold text-lg">
          <span class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm">⚡</span>
          AgentForge
        </a>
        <div class="flex items-center gap-1 sm:gap-2 overflow-x-auto">
          ${navLink("#/", "Dashboard", path)}
          ${navLink("#/agents", "Agents", path)}
          ${navLink("#/chat", "Chat", path)}
          ${navLink("#/tasks", "Tasks", path)}
          ${navLink("#/triggers", "Triggers", path)}
          ${navLink("#/integrations", "Integrations", path)}
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="hidden sm:block text-sm text-slate-400 max-w-[120px] truncate">${esc(state.user?.name || "")}</span>
          <button onclick="logout()" class="btn btn-ghost btn-sm" title="Log out">⏻</button>
        </div>
      </div>
    </nav>
    <main class="flex-1 w-full max-w-7xl mx-auto px-4 py-6 fade-in">${await pageBody(path)}</main>
    <footer class="border-t border-slate-800/60 py-5 text-center text-xs text-slate-600">
      AgentForge v1.0.0 · Build agents · Chat · Automate · <a href="/docs" class="text-slate-500 hover:text-blue-400">API docs</a>
    </footer>`;
  app.innerHTML = body;
  await pageScript(path);
}

function navLink(href, label, current) {
  const active = current.startsWith(href) && href !== "#/" ? "text-blue-400 bg-blue-500/10" : "text-slate-400 hover:text-slate-200";
  return `<a href="${href}" class="px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${active}">${label}</a>`;
}

async function pageBody(path) {
  if (path === "#/" || path === "") return dashboardPage();
  if (path.startsWith("#/agents")) return agentsPage();
  if (path.startsWith("#/chat")) return chatPage();
  if (path.startsWith("#/tasks")) return tasksPage();
  if (path.startsWith("#/triggers")) return triggersPage();
  if (path.startsWith("#/integrations")) return integrationsPage();
  return `<div class="py-20 text-center text-slate-500">Page not found</div>`;
}

async function pageScript(path) {
  if (path === "#/" || path === "") await dashboardScript();
  if (path.startsWith("#/agents")) await agentsScript();
  if (path.startsWith("#/chat")) await chatScript();
  if (path.startsWith("#/tasks")) await tasksScript();
  if (path.startsWith("#/triggers")) await triggersScript();
  if (path.startsWith("#/integrations")) await integrationsScript();
}

/* ---------------- Auth ---------------- */
function renderAuth(app, mode) {
  const isLogin = mode === "login";
  app.innerHTML = `
    <div class="flex-1 flex items-center justify-center p-4">
      <div class="w-full max-w-md">
        <div class="text-center mb-8">
          <span class="inline-flex w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 items-center justify-center text-2xl mb-4">⚡</span>
          <h1 class="text-3xl font-extrabold">AgentForge</h1>
          <p class="text-slate-400 mt-2">Your AI agents, working for you.</p>
        </div>
        <div class="card p-6">
          <h2 class="text-lg font-bold mb-4">${isLogin ? "Welcome back" : "Create your account"}</h2>
          ${isLogin ? "" : `<div class="mb-4"><label class="label">Full name</label><input id="auth-name" class="input" placeholder="ABraz Baloch" /></div>`}
          <div class="mb-4"><label class="label">Email</label><input id="auth-email" class="input" type="email" placeholder="you@example.com" /></div>
          <div class="mb-6"><label class="label">Password</label><input id="auth-password" class="input" type="password" placeholder="8+ chars, letters + digits" /></div>
          <button class="btn btn-primary w-full" onclick="${isLogin ? "doLogin()" : "doRegister()"}">${isLogin ? "Log in" : "Create account"}</button>
          <p class="text-sm text-slate-500 mt-4 text-center">
            ${isLogin ? "New here?" : "Already have an account?"}
            <a href="${isLogin ? "#/register" : "#/login"}" class="text-blue-400 hover:underline">${isLogin ? "Create an account" : "Log in"}</a>
          </p>
        </div>
        <p class="text-center text-xs text-slate-600 mt-6">Demo mode? Create any account — the demo agent is ready to chat.</p>
      </div>
    </div>`;
}

async function doLogin() {
  const email = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;
  try {
    const data = await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    state.token = data.access_token;
    localStorage.setItem("agf_token", state.token);
    state.user = data.user;
    window.location.hash = "#/";
    toast("Welcome back, " + (data.user.name || "friend") + "! 👋", "success");
  } catch (e) { toast(e.message, "error"); }
}

async function doRegister() {
  const name = document.getElementById("auth-name").value.trim();
  const email = document.getElementById("auth-email").value.trim();
  const password = document.getElementById("auth-password").value;
  try {
    const data = await api("/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) });
    state.token = data.access_token;
    localStorage.setItem("agf_token", state.token);
    state.user = data.user;
    window.location.hash = "#/";
    toast("Account created — welcome aboard! 🚀", "success");
  } catch (e) { toast(e.message, "error"); }
}

function logout() {
  state.token = ""; state.user = null;
  localStorage.removeItem("agf_token");
  window.location.hash = "#/login";
}

/* ---------------- WebSocket ---------------- */
function connectWS() {
  if (!state.token || (state.ws && state.ws.readyState === WebSocket.OPEN)) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  try {
    state.ws = new WebSocket(`${proto}://${location.host}/api/triggers/ws`);
    state.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "task_status" && (state.route.startsWith("#/tasks") || state.route.startsWith("#/"))) {
          refreshTasksSoon();
        }
      } catch (_) { /* ignore */ }
    };
    state.ws.onclose = () => { state.ws = null; setTimeout(connectWS, 5000); };
  } catch (_) { /* ignore */ }
}

let tasksRefreshTimer = null;
function refreshTasksSoon() {
  clearTimeout(tasksRefreshTimer);
  tasksRefreshTimer = setTimeout(async () => {
    try { state.tasks = await api("/tasks"); } catch (_) {}
    if (state.route.startsWith("#/tasks")) await tasksScript();
    else if (state.route.startsWith("#/")) { renderStats(); }
  }, 600);
}

window.addEventListener("hashchange", () => { router(); connectWS(); });
document.addEventListener("DOMContentLoaded", () => { router(); connectWS(); });
