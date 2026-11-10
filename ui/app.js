const { expensesUrl, settlementsUrl, apiKey } = window.APP_CONFIG;
const TIMEOUT_MS = 5000;

// Every call has a timeout, so a service that is down shows a message
// instead of hanging the page.
async function api(baseUrl, path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(baseUrl + path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey, ...options.headers },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function showHealth(elementId, baseUrl) {
  const el = document.getElementById(elementId);
  try {
    await api(baseUrl, "/health");
    el.textContent = "up";
    el.className = "status up";
  } catch {
    el.textContent = "unavailable";
    el.className = "status down";
  }
}

showHealth("expenses-status", expensesUrl);
showHealth("settlements-status", settlementsUrl);

// ---------- Group page ----------

function formatMoney(cents, currency) {
  return new Intl.NumberFormat("en-IE", { style: "currency", currency }).format(cents / 100);
}

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text; // textContent, not innerHTML, so names can't inject HTML
  if (className) td.className = className;
  return td;
}

// Sprint 1: replace the fake data with api(expensesUrl, `/groups/${id}`) and friends.
async function loadGroup() {
  return window.FAKE_DATA;
}

function renderGroup({ group, members, expenses }) {
  document.getElementById("group-name").textContent = group.name;

  const memberItems = members.map((m) => {
    const li = document.createElement("li");
    li.textContent = m.name;
    return li;
  });
  document.getElementById("member-list").replaceChildren(...memberItems);

  const names = new Map(members.map((m) => [m.id, m.name]));
  const rows = expenses.map((e) => {
    const tr = document.createElement("tr");
    tr.append(
      cell(e.description),
      cell(names.get(e.payer_id) ?? "Unknown"),
      cell(formatMoney(e.amount_cents, group.currency), "amount"),
    );
    return tr;
  });
  if (rows.length === 0) {
    const tr = document.createElement("tr");
    const td = cell("No expenses yet.");
    td.colSpan = 3;
    tr.append(td);
    rows.push(tr);
  }
  document.getElementById("expense-rows").replaceChildren(...rows);

  const total = expenses.reduce((sum, e) => sum + e.amount_cents, 0);
  document.getElementById("expense-total").textContent = formatMoney(total, group.currency);
}

async function showGroup() {
  try {
    renderGroup(await loadGroup());
  } catch {
    document.getElementById("group").textContent = "Could not load the group. Try again shortly.";
  }
}

showGroup();
