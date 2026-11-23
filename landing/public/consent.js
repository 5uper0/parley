(function () {
  var self = document.currentScript;
  if (!self) return;
  var GA = self.getAttribute("data-ga") || "";
  var CL = self.getAttribute("data-clarity") || "";
  if (!GA && !CL) return;
  var KEY = "parley-consent";
  var PROD = location.hostname === "parleyprotocol.com";
  var granted = false;
  var T = {
    en: { label: "Analytics consent", text: "This site can use Google Analytics and Microsoft Clarity to count visits and see how pages are used. Nothing loads and no cookies are set unless you accept.", more: "Privacy", reject: "Reject", accept: "Accept" },
    es: { label: "Consentimiento de analítica", text: "Este sitio puede usar Google Analytics y Microsoft Clarity para contar visitas y ver cómo se usan las páginas. No se carga nada ni se guardan cookies si no aceptas.", more: "Privacidad (en inglés)", reject: "Rechazar", accept: "Aceptar" },
    uk: { label: "Згода на аналітику", text: "Цей сайт може використовувати Google Analytics і Microsoft Clarity, щоб рахувати візити й бачити, як користуються сторінками. Без вашої згоди нічого не завантажується і cookies не ставляться.", more: "Конфіденційність (англійською)", reject: "Відхилити", accept: "Прийняти" }
  };
  var L = T[(document.documentElement.lang || "en").slice(0, 2)] || T.en;
  if (!CL) {
    L = Object.assign({}, L, {
      text: L.text.replace(" and Microsoft Clarity", "").replace(" y Microsoft Clarity", "").replace(" і Microsoft Clarity", "")
    });
  }

  window.gtag = function () {
    if (granted && GA) (window.dataLayer = window.dataLayer || []).push(arguments);
  };

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function load() {
    if (!PROD || granted) return;
    granted = true;
    if (GA) {
      var g = document.createElement("script");
      g.async = true;
      g.src = "https://www.googletagmanager.com/gtag/js?id=" + GA;
      document.head.appendChild(g);
      window.gtag("js", new Date());
      window.gtag("config", GA);
    }
    if (CL) {
      (function (c, l, a, r, i, t, y) {
        c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
        t = l.createElement(r); t.async = 1; t.src = "https://www.clarity.ms/tag/" + i;
        y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
      })(window, document, "clarity", "script", CL);
      window.clarity("consentv2", { ad_Storage: "denied", analytics_Storage: "granted" });
    }
  }

  function clearCookies() {
    var host = location.hostname, parts = host.split(".");
    var domains = ["", host, "." + host, "." + parts.slice(-2).join(".")];
    document.cookie.split(";").forEach(function (c) {
      var n = c.split("=")[0].trim();
      if (!/^(_ga|_gid|_gat|_clck|_clsk|CLID|ANONCHK|MR|MUID|SM|SRM_B)/.test(n)) return;
      domains.forEach(function (d) {
        document.cookie = n + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + (d ? "; domain=" + d : "");
      });
    });
  }

  var bar, opener;
  function hide() {
    if (!bar) return;
    bar.hidden = true;
    document.body.style.paddingBottom = "";
    if (opener && opener.focus) opener.focus();
    opener = null;
  }
  function choose(v) {
    var was = granted;
    store(v);
    if (v === "accepted") load();
    else { clearCookies(); if (was) { location.reload(); return; } }
    hide();
  }
  function build() {
    var css = document.createElement("style");
    css.textContent =
      "#parley-consent{position:fixed;left:0;right:0;bottom:0;z-index:2147483000;background:#F6F7FB;color:#0A0B0D;border-top:1px solid #8A8FA3;padding:14px 20px;font:14px/1.5 Inter,system-ui,sans-serif;box-shadow:0 -4px 16px rgba(10,11,13,.12)}" +
      "#parley-consent[hidden]{display:none}" +
      "#parley-consent .pc-in{max-width:960px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:center;gap:10px 20px}" +
      "#parley-consent p{margin:0;flex:1 1 340px}" +
      "#parley-consent a{display:inline-flex;align-items:center;min-height:44px;color:#3730A3;text-decoration:underline;text-underline-offset:3px}" +
      "#parley-consent .pc-b{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}#parley-consent .pc-b a{margin-right:8px}" +
      "#parley-consent button{min-height:44px;min-width:104px;padding:0 20px;border:2px solid #0A0B0D;border-radius:999px;background:#0A0B0D;color:#fff;font:600 14px Inter,system-ui,sans-serif;cursor:pointer}" +
      "#parley-consent button:focus-visible,#parley-consent a:focus-visible{outline:3px solid #4F46E5;outline-offset:2px}";
    document.head.appendChild(css);
    bar = document.createElement("div");
    bar.id = "parley-consent";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", L.label);
    bar.hidden = true;
    bar.innerHTML = '<div class="pc-in"><p></p><div class="pc-b"><button type="button" data-v="rejected"></button><button type="button" data-v="accepted"></button></div></div>';
    var p = bar.querySelector("p");
    p.textContent = L.text;
    var a = document.createElement("a");
    a.href = "/privacy/"; a.textContent = L.more; a.setAttribute("hreflang", "en");
    bar.querySelector(".pc-b").insertBefore(a, bar.querySelector("button"));
    var bs = bar.querySelectorAll("button");
    bs[0].textContent = L.reject; bs[1].textContent = L.accept;
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-v]");
      if (b) choose(b.getAttribute("data-v"));
    });
    document.body.insertBefore(bar, document.body.firstChild);
  }
  function show(fromOpener) {
    if (!bar) build();
    opener = fromOpener || null;
    bar.hidden = false;
    document.body.style.paddingBottom = bar.offsetHeight + "px";
    if (fromOpener) bar.querySelector("button").focus();
  }

  function init() {
    var v = stored();
    if (v === "accepted") load();
    else if (v !== "rejected") show();
    document.addEventListener("click", function (e) {
      var o = e.target.closest("[data-consent-open]");
      if (o) { e.preventDefault(); show(o); }
    });
  }
  if (document.body) init();
  else document.addEventListener("DOMContentLoaded", init);
})();
