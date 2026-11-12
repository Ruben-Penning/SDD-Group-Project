const { expensesUrl, settlementsUrl, apiKey } = window.APP_CONFIG;
const TIMEOUT_MS = 5000;
const CURRENCY = "EUR"; // Groups have no currency column; the MVP is euros only.

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Every call has a timeout, so a service that is down shows a message
// instead of hanging the page. A 4xx error carries the API's own message.
async function api(baseUrl, path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(baseUrl + path, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey, ...options.headers },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = typeof body?.detail === "string" ? body.detail : `HTTP ${response.status}`;
      throw new ApiError(detail, response.status);
    }
    return response.status === 204 ? null : await response.json();
  } finally {
    clearTimeout(timer);
  }
}

const UNAVAILABLE = "The expenses service is unavailable right now. Try again shortly.";

// For forms: show the API's validation message (e.g. a duplicate name).
// Timeouts, network errors and 5xx all mean the service is unavailable.
function formError(err) {
  if (!(err instanceof ApiError) || err.status >= 500) return UNAVAILABLE;
  if (err.status === 422) return "Please check the values you entered.";
  return err.message;
}

// For lists: a 4xx while loading is our bug, not the user's, so keep it short.
function loadError(err, what) {
  if (!(err instanceof ApiError) || err.status >= 500) return UNAVAILABLE;
  return `Could not load ${what}.`;
}

// ---------- Health ----------

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

// ---------- Helpers ----------

function formatMoney(cents) {
  return new Intl.NumberFormat("en-IE", { style: "currency", currency: CURRENCY }).format(
    cents / 100,
  );
}

// textContent, never innerHTML, so names typed by users can't inject HTML.
function listItem(text) {
  const li = document.createElement("li");
  li.textContent = text;
  return li;
}

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

function messageRow(text) {
  const tr = document.createElement("tr");
  const td = cell(text);
  td.colSpan = 3;
  tr.append(td);
  return tr;
}

function currentGroupId() {
  const id = Number(new URLSearchParams(window.location.search).get("group"));
  return Number.isInteger(id) && id > 0 ? id : null;
}

// Runs a form's request with the button disabled, so a double click can't
// create the same thing twice. Shows the error under the form if it fails.
function handleSubmit(form, action) {
  const button = form.querySelector("button");
  const error = form.querySelector(".error");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = form.elements.name.value.trim();
    if (!name) {
      error.textContent = "Enter a name.";
      return;
    }
    button.disabled = true;
    error.textContent = "";
    try {
      await action(name);
      form.reset();
    } catch (err) {
      error.textContent = formError(err);
    } finally {
      button.disabled = false;
    }
  });
}

// ---------- Groups list (no ?group= in the URL) ----------

async function showGroups() {
  document.getElementById("groups-view").hidden = false;
  const list = document.getElementById("group-list");

  try {
    const groups = await api(expensesUrl, "/groups");
    const items = groups.map((g) => {
      const link = document.createElement("a");
      link.href = `?group=${g.id}`;
      link.textContent = g.name;
      const li = document.createElement("li");
      li.append(link);
      return li;
    });
    if (items.length === 0) items.push(listItem("No groups yet. Create the first one below."));
    list.replaceChildren(...items);
  } catch (err) {
    list.replaceChildren(listItem(loadError(err, "groups")));
  }

  handleSubmit(document.getElementById("new-group-form"), async (name) => {
    const group = await api(expensesUrl, "/groups", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    window.location.search = `?group=${group.id}`;
  });
}

// ---------- One group (?group=ID) ----------

async function loadMembers(groupId) {
  const list = document.getElementById("member-list");
  try {
    const members = await api(expensesUrl, `/groups/${groupId}/members`);
    const items = members.map((m) => listItem(m.name));
    if (items.length === 0) items.push(listItem("No members yet."));
    list.replaceChildren(...items);
    return members;
  } catch (err) {
    list.replaceChildren(listItem(loadError(err, "members")));
    return [];
  }
}

async function loadExpenses(groupId, members) {
  const rows = document.getElementById("expense-rows");
  const total = document.getElementById("expense-total");
  try {
    const expenses = await api(expensesUrl, `/groups/${groupId}/expenses`);
    const names = new Map(members.map((m) => [m.id, m.name]));
    const trs = expenses.map((e) => {
      const tr = document.createElement("tr");
      tr.append(
        cell(e.description),
        cell(names.get(e.paid_by_member_id) ?? "Unknown"),
        cell(formatMoney(e.amount_cents), "amount"),
      );
      return tr;
    });
    if (trs.length === 0) trs.push(messageRow("No expenses yet."));
    rows.replaceChildren(...trs);
    total.textContent = formatMoney(expenses.reduce((sum, e) => sum + e.amount_cents, 0));
  } catch (err) {
    rows.replaceChildren(messageRow(loadError(err, "expenses")));
    total.textContent = "";
  }
}

async function showGroup(groupId) {
  document.getElementById("group-view").hidden = false;
  const heading = document.getElementById("group-name");

  let group;
  try {
    group = await api(expensesUrl, `/groups/${groupId}`);
  } catch (err) {
    heading.textContent =
      err instanceof ApiError && err.status === 404 ? "Group not found." : UNAVAILABLE;
    return;
  }
  heading.textContent = group.name;
  document.title = `${group.name} · Splitwise-lite`;
  document.getElementById("group-details").hidden = false;

  const members = await loadMembers(groupId);
  await loadExpenses(groupId, members);

  handleSubmit(document.getElementById("new-member-form"), async (name) => {
    await api(expensesUrl, `/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    const updated = await loadMembers(groupId);
    await loadExpenses(groupId, updated);
  });
}

// ---------- Start ----------

showHealth("expenses-status", expensesUrl);
showHealth("settlements-status", settlementsUrl);

const groupId = currentGroupId();
if (groupId) {
  showGroup(groupId);
} else {
  showGroups();
}
