// Anonymous daily counters for the Room funnel (docs/room/analytics-events.md). No ids, no cookies,
// no address, nothing finer than a day. This module is pure; the Worker and the Counters object use it.

export const DEVICE_EVENTS = new Set(["page_start", "q_answered", "result_viewed_ok", "result_refused"]);
export const RELAY_EVENTS = new Set(["room_created", "joined", "submitted", "room_closed"]);
export const REJECT_CODES = new Set(["bad-token", "bad-signature", "bad-verdicts", "locked", "bad-organizer-key", "no-organizer"]);
export const LANGS = new Set(["en", "es"]);
export const MAX_BODY_BYTES = 128;
export const SMALL = 5;

/** Returns the counter key for a device beacon, or null. Never echoes anything from the input. */
export function beaconKey(text) {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > MAX_BODY_BYTES) return null;
  let b;
  try { b = JSON.parse(text); } catch { return null; }
  if (!b || typeof b !== "object" || Array.isArray(b)) return null;
  if (Object.keys(b).some((k) => !["event", "n", "lang"].includes(k))) return null;
  if (!DEVICE_EVENTS.has(b.event) || !LANGS.has(b.lang)) return null;
  if (b.event === "q_answered") {
    if (!Number.isInteger(b.n) || b.n < 1 || b.n > 4) return null;
    return `q_answered_${b.n}`;
  }
  if (b.event === "result_refused") {
    return b.n === undefined || b.n === null ? "result_refused" : null;
  }
  if (b.n !== undefined && b.n !== null) return null;
  return b.event;
}

export const dayOf = (ms) => new Date(ms).toISOString().slice(0, 10);

/** counters: {day: {key: n}}; adds one. */
export function bump(counters, day, key) {
  counters[day] = counters[day] || {};
  counters[day][key] = (counters[day][key] || 0) + 1;
  return counters;
}

/** Keep 90 days only. */
export function prune(counters, now, keepDays = 90) {
  const cut = dayOf(now - keepDays * 86400000);
  for (const d of Object.keys(counters)) if (d < cut) delete counters[d];
  return counters;
}

const monday = (day) => {
  const d = new Date(day + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
};

/** Weekly totals only; totals under SMALL are shown as "<5" so a quiet week cannot point at one room. */
export function weeklyReport(counters) {
  const weeks = {};
  for (const [day, row] of Object.entries(counters)) {
    const w = monday(day);
    weeks[w] = weeks[w] || {};
    for (const [k, n] of Object.entries(row)) weeks[w][k] = (weeks[w][k] || 0) + n;
  }
  return Object.fromEntries(Object.entries(weeks).sort().map(([w, row]) =>
    [w, Object.fromEntries(Object.entries(row).sort().map(([k, n]) => [k, n < SMALL ? "<5" : n]))]));
}

/** Relay-side event for a finished request, from path, method, status and the error code only. */
export function relayEventFor(method, path, status, errorCode, done) {
  if (status >= 400) return errorCode && REJECT_CODES.has(errorCode) ? `rejected_${errorCode}` : null;
  if (method === "POST" && path === "") return "room_created";
  if (method === "POST" && path === "/join") return "joined";
  if (method === "POST" && path === "/verdicts") return done ? "room_closed" : "submitted";
  return null;
}
