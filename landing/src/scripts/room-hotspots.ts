// Room hotspots are plain anchors, so they work with JS off. This adds the
// rest: focus moves to the opened section's heading, and Escape returns to the
// room's wide state.

function sectionOf(id: string): HTMLElement | null {
  const el = id ? document.getElementById(id) : null;
  return el ? el.closest<HTMLElement>(".film-section") : null;
}

function headingOf(section: HTMLElement): HTMLElement {
  const id = section.getAttribute("aria-labelledby");
  const h = (id && document.getElementById(id)) || section.querySelector<HTMLElement>("h2");
  const target = h ?? section;
  if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  return target;
}

function init(): void {
  const room = document.getElementById("room");
  if (!room) return;

  room.querySelectorAll<HTMLAnchorElement>("a[data-room-hotspot]").forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.hash.slice(1);
      const section = sectionOf(id);
      if (!section) return;
      e.preventDefault();
      // location.hash (not replaceState) so hashchange fires and the page marks the section.
      location.hash = id;
      section.scrollIntoView({ block: "start" });
      headingOf(section).focus({ preventScroll: true });
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || e.defaultPrevented) return;
    if (document.querySelector('#film-nav[data-open="true"]')) return;
    if (!sectionOf(location.hash.slice(1))) return;
    location.hash = "room";
    room.scrollIntoView({ block: "start" });
    room.focus({ preventScroll: true });
  });
}

init();
