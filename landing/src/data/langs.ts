export type Lang = "en" | "es" | "uk";

const GROUP = {
  en: "/spain-inherited-flat-do-all-heirs-have-to-agree/",
  es: "/es/unanimidad-vender-piso-heredado/",
  uk: "/uk/zghoda-spadkoyemtsiv-prodazh-kvartyry/",
};
const ES_SIBLING = "/es/reparto-de-herencia-entre-hermanos/";

// Translated pairs are real translations (same hreflang set the pages declare in <head>).
// A page with no translation links each other language to that language's entry guide, so the
// switcher is never a dead end; the destination states its own language.
export function langTargets(pathname: string, current: Lang): Record<Lang, string> {
  const path = pathname.endsWith("/") ? pathname : `${pathname}/`;
  if (Object.values(GROUP).includes(path)) return { ...GROUP };
  if (path === "/404/") return { en: "/", es: ES_SIBLING, uk: GROUP.uk };
  if (path === ES_SIBLING) return { en: "/", es: ES_SIBLING, uk: GROUP.uk };
  return { en: current === "en" ? path : "/", es: ES_SIBLING, uk: GROUP.uk };
}
