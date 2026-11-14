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

// A problem with what the user typed, caught before calling the API.
class FormError extends Error {}

// Turns what the user typed ("12", "12.5", "12,50") into integer cents, without
// going through a float, so 0.1 + 0.2 rounding can never creep in.
function parseAmountToCents(text) {
  const match = text.trim().replace(",", ".").match(/^(\d{1,7})(?:\.(\d{1,2}))?$/);
  if (!match) throw new FormError("Enter an amount like 12.50 (up to 2 decimals).");
  const cents = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  if (cents === 0) throw new FormError("The amount must be more than 0.");
  return cents;
}

function requiredText(form, field, message) {
  const value = form.elements[field].value.trim();
  if (!value) throw new FormError(message);
  return value;
}

// Runs a form's request with the button disabled, so a double click can't
// create the same thing twice. Shows the error under the form if it fails.
// `action` gets the form, reads its fields and throws FormError for bad input.
function handleSubmit(form, action) {
  const button = form.querySelector("button");
  const error = form.querySelector(".error");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    error.textContent = "";
    try {
      await action(form);
      form.reset();
    } catch (err) {
      error.textContent = err instanceof FormError ? err.message : formError(err);
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

  handleSubmit(document.getElementById("new-group-form"), async (form) => {
    const name = requiredText(form, "name", "Enter a name.");
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

  let members = await loadMembers(groupId);
  await loadExpenses(groupId, members);
  renderExpenseForm(members);

  handleSubmit(document.getElementById("new-member-form"), async (form) => {
    const name = requiredText(form, "name", "Enter a name.");
    await api(expensesUrl, `/groups/${groupId}/members`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    members = await loadMembers(groupId);
    await loadExpenses(groupId, members);
    renderExpenseForm(members);
  });

  const expenseForm = document.getElementById("new-expense-form");
  handleSubmit(expenseForm, async (form) => {
    const body = readExpenseForm(form);
    await api(expensesUrl, `/groups/${groupId}/expenses`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    await loadExpenses(groupId, members);
  });
  // form.reset() unticks nothing we ticked in code, so re-tick everyone after each reset.
  expenseForm.addEventListener("reset", () => setTimeout(() => renderExpenseForm(members)));
}

// ---------- Add expense form ----------

// Fills "Paid by" and the "Split between" checkboxes from the member list.
// Everyone is ticked by default: most expenses are shared by the whole group.
function renderExpenseForm(members) {
  const form = document.getElementById("new-expense-form");
  const hasMembers = members.length > 0;
  form.hidden = !hasMembers;
  document.getElementById("expense-form-note").hidden = hasMembers;

  const options = members.map((m) => {
    const option = document.createElement("option");
    option.value = String(m.id);
    option.textContent = m.name;
    return option;
  });
  form.elements.payer.replaceChildren(...options);

  const checks = members.map((m) => {
    const box = document.createElement("input");
    box.type = "checkbox";
    box.name = "split";
    box.value = String(m.id);
    box.checked = true;
    const label = document.createElement("label");
    label.className = "check";
    label.append(box, ` ${m.name}`);
    return label;
  });
  document.getElementById("expense-split").replaceChildren(...checks);
}

// Reads and checks the form, returning the body POST /groups/{id}/expenses expects.
// The service does the equal split itself, so the UI only sends who shares it.
function readExpenseForm(form) {
  const description = requiredText(form, "description", "Enter a description.");
  const amountCents = parseAmountToCents(form.elements.amount.value);
  const memberIds = [...form.querySelectorAll('input[name="split"]:checked')].map((box) =>
    Number(box.value),
  );
  if (memberIds.length === 0) throw new FormError("Tick at least one person to split with.");
  return {
    description,
    amount_cents: amountCents,
    paid_by_member_id: Number(form.elements.payer.value),
    member_ids: memberIds,
  };
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
