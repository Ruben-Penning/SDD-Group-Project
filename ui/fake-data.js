// Temporary sample data for the group page, shaped like the expenses-service API.
// Delete this file once the page reads from the API (Sprint 1).
window.FAKE_DATA = {
  group: { id: 1, name: "Lisbon trip", currency: "EUR" },
  members: [
    { id: 1, group_id: 1, name: "Ana" },
    { id: 2, group_id: 1, name: "Ben" },
    { id: 3, group_id: 1, name: "Carla" },
  ],
  expenses: [
    { id: 1, group_id: 1, payer_id: 1, description: "Hotel", amount_cents: 24000 },
    { id: 2, group_id: 1, payer_id: 2, description: "Dinner", amount_cents: 7550 },
    { id: 3, group_id: 1, payer_id: 3, description: "Tram tickets", amount_cents: 1000 },
  ],
};