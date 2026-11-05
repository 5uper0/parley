// Parley engine for the browser and Node. No dependencies. A port of parley/spec.py,
// parley/preferences.py, parley/agent.py, parley/consensus.py and the transcript hash in
// parley/transcript.py; held to the Python answers by tests/golden/engine_vectors.json.
//
// Known limit: JSON loses 1 vs 1.0, so an option number written as an integer-valued float
// (5.0) canonicalises as 5 here and 5.0 in Python. Write whole numbers without a decimal point.

const MISSING = Symbol("missing");

/** A number that must print the way Python prints a float (1.0, 1e-07). */
export class Fl {
  constructor(v) { this.v = v; }
}

function pyFloatRepr(x) {
  if (Number.isNaN(x) || !Number.isFinite(x)) throw new Error("non-finite number");
  if (x === 0) return Object.is(x, -0) ? "-0.0" : "0.0";
  const [mant, exp] = x.toExponential().split("e");
  const sign = mant.startsWith("-") ? "-" : "";
  const digits = mant.replace("-", "").replace(".", "");
  const e = parseInt(exp, 10);
  const decpt = e + 1;
  if (decpt > -4 && decpt <= 16) {
    if (decpt <= 0) return sign + "0." + "0".repeat(-decpt) + digits;
    if (digits.length <= decpt) return sign + digits + "0".repeat(decpt - digits.length) + ".0";
    return sign + digits.slice(0, decpt) + "." + digits.slice(decpt);
  }
  const m = digits.length === 1 ? digits : digits[0] + "." + digits.slice(1);
  return `${sign}${m}e${e < 0 ? "-" : "+"}${String(Math.abs(e)).padStart(2, "0")}`;
}

function cmpCodePoint(a, b) {
  const A = Array.from(a), B = Array.from(b);
  for (let i = 0; i < Math.min(A.length, B.length); i++) {
    const d = A[i].codePointAt(0) - B[i].codePointAt(0);
    if (d) return d;
  }
  return A.length - B.length;
}

/** json.dumps(obj, sort_keys=True, ensure_ascii=False) */
export function canonicalJson(obj) {
  if (obj === null || obj === undefined) return "null";
  if (obj instanceof Fl) return pyFloatRepr(obj.v);
  if (typeof obj === "boolean") return obj ? "true" : "false";
  if (typeof obj === "number") return Number.isInteger(obj) ? String(obj) : pyFloatRepr(obj);
  if (typeof obj === "string") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonicalJson).join(", ") + "]";
  return "{" + Object.keys(obj).sort(cmpCodePoint)
    .map((k) => JSON.stringify(k) + ": " + canonicalJson(obj[k])).join(", ") + "}";
}

export async function sha256Hex(text) {
  const buf = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, "0")).join("");
}

const isNum = (x) => typeof x === "number";
const sameKind = (a, b) => (typeof a === "boolean") === (typeof b === "boolean");

/** Python == : True equals 1, containers compare by content. */
function looseEq(a, b) {
  const scalar = (x) => typeof x === "boolean" || typeof x === "number";
  if (scalar(a) && scalar(b)) return Number(a) === Number(b);
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => looseEq(v, b[i]));
  if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
    const ka = Object.keys(a), kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => Object.hasOwn(b, k) && looseEq(a[k], b[k]));
  }
  return a === b;
}

/** parley/spec.py _strict_eq: bool stays apart from int at every depth, so [true] is not [1]. */
function strictEq(a, b) {
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => strictEq(v, b[i]));
  const isObj = (x) => x && typeof x === "object" && !Array.isArray(x);
  if (isObj(a) && isObj(b)) {
    const ka = Object.keys(a), kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => Object.hasOwn(b, k) && strictEq(a[k], b[k]));
  }
  return sameKind(a, b) && looseEq(a, b);
}

const get = (option, attr) => (Object.hasOwn(option, attr) ? option[attr] : MISSING);

export function checkConstraint(c, option) {
  const val = get(option, c.attr);
  if (val === MISSING) return false;
  switch (c.op) {
    case "==": return strictEq(val, c.value);
    case "!=":
      if (looseEq(val, c.value) && !strictEq(val, c.value)) return false;
      return !looseEq(val, c.value);
    case "<": case "<=": case ">": case ">=":
      if (!(isNum(val) && isNum(c.value))) return false;
      return c.op === "<" ? val < c.value : c.op === "<=" ? val <= c.value
        : c.op === ">" ? val > c.value : val >= c.value;
    case "in": return c.value.some((v) => strictEq(val, v));
    case "not_in":
      if (c.value.some((v) => looseEq(val, v) && !strictEq(val, v))) return false;
      return !c.value.some((v) => looseEq(val, v));
    default: throw new Error(`unknown operator: ${c.op}`);
  }
}

function toFloat(val) {
  if (typeof val === "boolean") return val ? 1 : 0;
  if (typeof val === "number") return val;
  if (typeof val === "string" && val.trim() !== "" && !Number.isNaN(Number(val))) return Number(val);
  throw new Error("could not convert value to float");
}

function termScore(t, option) {
  const val = get(option, t.attr);
  const weight = t.weight ?? 1.0;
  if (t.prefer !== undefined && t.prefer !== null) {
    return [val !== MISSING && looseEq(val, t.prefer) ? weight : 0, weight];
  }
  if (t.direction && val !== MISSING && t.lo != null && t.hi != null) {
    const span = t.hi - t.lo;
    let norm = span === 0 ? 0 : (toFloat(val) - t.lo) / span;
    norm = Math.max(0, Math.min(1, norm));
    if (t.direction === "lower") norm = 1 - norm;
    return [weight * norm, weight];
  }
  return [0, weight];
}

/** One party's private sheet applied to one option -> {feasible, score}. Never leaves the device. */
export function evaluate(party, option) {
  const feasible = (party.hard || []).every((c) => checkConstraint(c, option));
  const terms = party.utility || [];
  let score = 0.5;
  if (terms.length) {
    let got = 0, tot = 0;
    for (const t of terms) { const [c, w] = termScore(t, option); got += c; tot += w; }
    const raw = tot ? got / tot : 0.5;
    if (Number.isNaN(raw)) throw new Error("utility returned NaN");
    score = Math.max(0, Math.min(1, raw));
  }
  return { feasible, score };
}

/** The only thing that may leave a device. */
export function verdictFor(party, option) {
  const ev = evaluate(party, option);
  // A red-lined verdict carries the constant 0, as parley/agent.py does: a rejected option's real score only leaks preference data.
  return { owner: party.owner, acceptable: ev.feasible, score: ev.feasible ? ev.score : 0,
           reason: ev.feasible ? "ok" : "red-line" };
}

/** Max-min over verdicts feasible for everyone; honest deadlock if none. */
export function chooseFromEntries(entries) {
  let best = null;
  for (const e of entries) {
    if (e.verdicts.length && e.verdicts.every((v) => v.acceptable)) {
      const floor = Math.min(...e.verdicts.map((v) => v.score));
      const total = e.verdicts.reduce((s, v) => s + v.score, 0);
      if (best === null || floor > best.floor || (floor === best.floor && total > best.total)) {
        best = { option: e.option, floor, total };
      }
    }
  }
  return best ? { status: "agreed", decision: best.option } : { status: "deadlock", decision: null };
}

export async function transcriptHash(entries, result) {
  const record = {
    entries: entries.map((e) => ({
      option: e.option,
      verdicts: e.verdicts.map((v) => ({ owner: v.owner, acceptable: v.acceptable, score: new Fl(v.score),
                                         reason: v.reason, sig: null, pubkey_hex: null })),
    })),
    result: { status: result.status, decision: result.decision },
  };
  return sha256Hex(canonicalJson(record));
}

/** Run a whole spec in one place (tests, demos). In the Room each party calls verdictFor on its own device. */
export async function runSpec(spec) {
  const entries = spec.options.map((option) => ({
    option, verdicts: spec.parties.map((p) => verdictFor(p, option)),
  }));
  const result = chooseFromEntries(entries);
  return { ...result, entries, transcriptHash: await transcriptHash(entries, result) };
}
