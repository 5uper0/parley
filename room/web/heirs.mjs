// J1 template "flat or house" and the step that turns six plain answers into a private sheet.
// Everything here runs on the person's device. Q5 (what you would give up) and Q6 (fallback)
// are shown on the check screen only: the engine does not use them in this slice.

export const HEIRS_OPTIONS = [
  { id: "sell_now",  months_to_money: 3,   monthly_cost: 0,   keeps_home: false, forces_out: true },
  { id: "sell_year", months_to_money: 12,  monthly_cost: 100, keeps_home: false, forces_out: true },
  { id: "buyout",    months_to_money: 6,   monthly_cost: 0,   keeps_home: true,  forces_out: false },
  { id: "rent_out",  months_to_money: 24,  monthly_cost: 0,   keeps_home: true,  forces_out: false },
  { id: "keep",      months_to_money: 120, monthly_cost: 300, keeps_home: true,  forces_out: false },
];
const OPTION_IDS = new Set(HEIRS_OPTIONS.map((o) => o.id));
export const PRIORITIES = ["money", "speed", "home", "fairness"];

const isInt = (x, max = 1200) => Number.isInteger(x) && x >= 0 && x <= max;

/** answers: {favourite|null, never:[ids], maxMonths|null, maxMonthly|null, mustKeepHome, noOneForcedOut,
 *            priorities:[3 of PRIORITIES, most important first]} */
export function sheetFromAnswers(owner, a) {
  if (a.favourite != null && !OPTION_IDS.has(a.favourite)) throw new Error("bad-answer");
  if (!Array.isArray(a.never) || !a.never.every((id) => OPTION_IDS.has(id))) throw new Error("bad-answer");
  if (a.maxMonths != null && !isInt(a.maxMonths)) throw new Error("bad-answer");
  if (a.maxMonthly != null && !isInt(a.maxMonthly, 1_000_000)) throw new Error("bad-answer");
  if (!Array.isArray(a.priorities) || a.priorities.length > 3
      || !a.priorities.every((p) => PRIORITIES.includes(p)) || new Set(a.priorities).size !== a.priorities.length) {
    throw new Error("bad-answer");
  }
  const hard = [];
  if (a.never.length) hard.push({ attr: "id", op: "not_in", value: [...a.never] });
  if (a.maxMonths != null) hard.push({ attr: "months_to_money", op: "<=", value: a.maxMonths });
  if (a.maxMonthly != null) hard.push({ attr: "monthly_cost", op: "<=", value: a.maxMonthly });
  if (a.mustKeepHome) hard.push({ attr: "keeps_home", op: "==", value: true });
  if (a.noOneForcedOut) hard.push({ attr: "forces_out", op: "==", value: false });

  const utility = [];
  if (a.favourite != null) utility.push({ attr: "id", prefer: a.favourite, weight: 3 });
  const termFor = {
    money: (w) => ({ attr: "monthly_cost", direction: "lower", lo: 0, hi: 500, weight: w }),
    speed: (w) => ({ attr: "months_to_money", direction: "lower", lo: 0, hi: 120, weight: w }),
    home: (w) => ({ attr: "keeps_home", prefer: true, weight: w }),
    fairness: (w) => ({ attr: "forces_out", prefer: false, weight: w }),
  };
  a.priorities.forEach((p, i) => utility.push(termFor[p](3 - i)));
  return { owner, hard, utility };
}

/** The check screen: each rule as a plain sentence key plus its value, for the UI to translate. */
export function describeAnswers(a) {
  const lines = [];
  if (a.never.length) lines.push({ key: "never", options: [...a.never] });
  if (a.maxMonths != null) lines.push({ key: "maxMonths", n: a.maxMonths });
  if (a.maxMonthly != null) lines.push({ key: "maxMonthly", n: a.maxMonthly });
  if (a.mustKeepHome) lines.push({ key: "mustKeepHome" });
  if (a.noOneForcedOut) lines.push({ key: "noOneForcedOut" });
  if (a.favourite != null) lines.push({ key: "favourite", option: a.favourite });
  if (a.priorities.length) lines.push({ key: "priorities", order: [...a.priorities] });
  return lines;
}
