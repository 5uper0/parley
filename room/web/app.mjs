// Phone page. One column, one button per screen. Hash routes: "#/" organizer, "#/r/<room>/<name>" a person.
import { T, pickLang } from "./i18n.mjs";
import { HEIRS_OPTIONS, sheetFromAnswers, describeAnswers, PRIORITIES } from "./heirs.mjs";
import { newDevice, restoreDevice, createRoom, joinRoom, submitAnswers, getStatus, getResult } from "./client.mjs";

const RELAY = window.PARLEY_RELAY || "";
const $app = document.getElementById("app");
let lang = pickLang(navigator);
const t = () => T[lang];
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k.startsWith("on") ? n.addEventListener(k.slice(2), v) : n.setAttribute(k, v);
  for (const k of kids.flat()) n.append(k);
  return n;
};
const show = (...nodes) => { $app.replaceChildren(...nodes); window.scrollTo(0, 0); };
const btn = (label, onclick, cls = "") => el("button", { type: "button", class: cls, onclick }, label);
const langSwitch = () => el("p", { class: "lang" }, ...["en", "es"].map((l) =>
  el("button", { type: "button", class: l === lang ? "on" : "", onclick: () => { lang = l; route(); } }, l.toUpperCase())));
const fail = (msg) => show(langSwitch(), el("p", { class: "err" }, msg));
const optName = (id) => t().opt[id];

function home() {
  show(langSwitch(), el("h1", {}, t().title), el("p", {}, t().lead), el("p", { class: "note" }, t().notLegal),
    btn(t().start, who, "primary"));
}

function who() {
  const ta = el("textarea", { rows: "5", autocomplete: "off" });
  show(langSwitch(), el("h2", {}, t().whoTitle), el("p", { class: "note" }, t().whoHint), ta,
    btn(t().makeLinks, async () => {
      const owners = ta.value.split("\n").map((s) => s.trim()).filter(Boolean);
      try {
        const room = await createRoom(fetch, RELAY, { options: HEIRS_OPTIONS, owners });
        share(room.id, owners);
      } catch { fail(t().err); }
    }, "primary"));
}

function share(id, owners) {
  const base = location.href.split("#")[0];
  show(langSwitch(), el("h2", {}, t().shareTitle), ...owners.map((name) => {
    const url = `${base}#/r/${id}/${encodeURIComponent(name)}`;
    return el("div", { class: "card" }, el("strong", {}, name), el("code", {}, url),
      btn(t().copy, () => navigator.clipboard?.writeText(url)),
      el("a", { class: "button", href: `https://wa.me/?text=${encodeURIComponent(t().waText(name, url))}`, target: "_blank", rel: "noopener" }, t().whatsapp));
  }));
}

const key = (id, owner) => `parley-room-${id}-${owner}`;

async function person(id, owner) {
  let status;
  try { status = await getStatus(fetch, RELAY, id); } catch { return fail(t().lost); }
  if (!status.owners.includes(owner)) return fail(t().lost);
  show(langSwitch(), el("h1", {}, t().joinTitle(owner)), el("p", {}, t().joinLead), el("p", { class: "note" }, t().notLegal),
    btn(t().start, () => { if (status.submitted.includes(owner)) return waiting(id, owner); questions(id, owner, status); }, "primary"));
}

function questions(id, owner, status) {
  const a = { favourite: null, never: [], maxMonths: null, maxMonthly: null, mustKeepHome: false, noOneForcedOut: false, priorities: [] };
  const ids = HEIRS_OPTIONS.map((o) => o.id);
  const radio = (name, value, label, checked) => el("label", {}, el("input", { type: "radio", name, value, ...(checked ? { checked: "" } : {}) }), ` ${label}`);
  const steps = [
    () => { const ch = el("div", {}, ...ids.map((o) => radio("fav", o, optName(o))), radio("fav", "", t().q1none, true));
      return [t().q1, ch, () => { a.favourite = ch.querySelector("input:checked").value || null; }]; },
    () => { const ch = el("div", {}, ...ids.map((o) => el("label", {}, el("input", { type: "checkbox", value: o }), ` ${optName(o)}`)));
      return [t().q2, el("div", {}, el("p", { class: "note" }, t().q2hint), ch), () => { a.never = [...ch.querySelectorAll("input:checked")].map((i) => i.value); }]; },
    () => { const m = el("input", { type: "number", min: "0", inputmode: "numeric" }), c = el("input", { type: "number", min: "0", inputmode: "numeric" });
      const h = el("input", { type: "checkbox" }), f = el("input", { type: "checkbox" });
      return [t().q3, el("div", {}, el("label", {}, t().q3months, m), el("label", {}, t().q3monthly, c), el("label", {}, h, ` ${t().q3home}`), el("label", {}, f, ` ${t().q3forced}`)),
        () => { a.maxMonths = m.value === "" ? null : Number(m.value); a.maxMonthly = c.value === "" ? null : Number(c.value); a.mustKeepHome = h.checked; a.noOneForcedOut = f.checked; }]; },
    () => { const picked = []; const box = el("div", {}); const draw = () => box.replaceChildren(...PRIORITIES.map((p) => {
        const i = picked.indexOf(p);
        return el("button", { type: "button", class: i >= 0 ? "on" : "", onclick: () => { i >= 0 ? picked.splice(i, 1) : picked.length < 3 && picked.push(p); draw(); } },
          `${i >= 0 ? i + 1 + ". " : ""}${t().pri[p]}`); })); draw();
      return [t().q4, el("div", {}, el("p", { class: "note" }, t().q4hint), box), () => { a.priorities = [...picked]; }]; },
  ];
  const go = (i) => {
    if (i >= steps.length) return check(id, owner, status, a);
    const [title, body, collect] = steps[i]();
    show(langSwitch(), el("p", { class: "note" }, `${i + 1} / ${steps.length}`), el("h2", {}, title), body,
      i > 0 ? btn(t().back, () => go(i - 1)) : "", btn(t().next, () => { collect(); go(i + 1); }, "primary"));
  };
  go(0);
}

function check(id, owner, status, a) {
  const L = t().line, names = (xs) => xs.map(optName).join(", ");
  const lines = describeAnswers(a).map((l) => ({
    never: () => L.never(names(l.options)), maxMonths: () => L.maxMonths(l.n), maxMonthly: () => L.maxMonthly(l.n),
    mustKeepHome: () => L.mustKeepHome(), noOneForcedOut: () => L.noOneForcedOut(), favourite: () => L.favourite(optName(l.option)),
    priorities: () => L.priorities(l.order.map((p) => t().pri[p]).join(", ")),
  })[l.key]());
  show(langSwitch(), el("h2", {}, t().checkTitle), el("p", { class: "note" }, t().checkLead), el("ul", {}, ...lines.map((s) => el("li", {}, s))),
    btn(t().back, () => questions(id, owner, status)),
    btn(t().confirm, async () => {
      show(el("p", {}, t().sending));
      try {
        const device = await newDevice();
        localStorage.setItem(key(id, owner), JSON.stringify(device.privateJwk));
        const { session, nonces } = await joinRoom(fetch, RELAY, id, owner, device);
        await submitAnswers(fetch, RELAY, id, { owner, sheet: sheetFromAnswers(owner, a), options: status.options, session, nonces, device });
        waiting(id, owner);
      } catch { fail(t().err); }
    }, "primary"));
}

async function waiting(id, owner) {
  let result;
  try { result = await getResult(fetch, RELAY, id); } catch { return fail(t().err); }
  if (result) return showResult(result);
  const st = await getStatus(fetch, RELAY, id).catch(() => null);
  const left = st ? st.owners.filter((o) => !st.submitted.includes(o)).join(", ") : "";
  show(langSwitch(), el("h2", {}, t().waitTitle), el("p", {}, t().waitLead(left)));
  setTimeout(() => waiting(id, owner), 3000);
}

function showResult(r) {
  const agreed = r.status === "agreed";
  show(langSwitch(), el("h2", {}, agreed ? t().agreedTitle : t().deadTitle),
    agreed ? el("p", { class: "big" }, optName(r.decision.id)) : "", el("p", { class: "note" }, agreed ? t().agreedNote : t().deadNote),
    el("h3", {}, t().recordTitle), el("p", {}, t().recordLead, ": ", el("code", {}, r.transcript_hash.slice(0, 12))),
    el("p", { class: "note" }, t().notLegal), btn(t().save, () => window.print()));
}

function route() {
  const m = location.hash.match(/^#\/r\/([0-9a-f]{32})\/(.+)$/);
  m ? person(m[1], decodeURIComponent(m[2])) : home();
}
window.addEventListener("hashchange", route);
route();
