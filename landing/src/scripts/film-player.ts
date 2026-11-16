// Film player for /film/. Without this script (or with reduced motion) the
// markup stays in its static state: poster plus all captions as plain text.

export function initFilmPlayer(root: ParentNode = document): void {
  root.querySelectorAll<HTMLElement>("[data-film-player]").forEach(setup);
}

function setup(el: HTMLElement): void {
  // The inline script in FilmPlayer.astro sets data-js before first paint,
  // and skips it for prefers-reduced-motion. No data-js means poster only.
  if (!el.hasAttribute("data-js")) return;

  const video = el.querySelector<HTMLVideoElement>("video");
  const toggle = el.querySelector<HTMLButtonElement>("[data-film-toggle]");
  const replay = el.querySelector<HTMLButtonElement>("[data-film-replay]");
  const caps = Array.from(el.querySelectorAll<HTMLElement>("[data-at]"));
  if (!video || !toggle || !replay) return;

  // Same URL the <picture> already picked, so no second poster download.
  const img = el.querySelector<HTMLImageElement>("img");
  if (img?.currentSrc) video.poster = img.currentSrc;

  const showCaption = () => {
    const t = video.currentTime;
    let active = caps[0];
    for (const c of caps) if (t >= Number(c.dataset.at)) active = c;
    for (const c of caps) c.classList.toggle("is-active", c === active);
  };

  const setToggle = (playing: boolean) => {
    const label = playing ? "Pause" : "Play";
    toggle.textContent = label;
    toggle.setAttribute("aria-label", `${label} the film`);
  };

  let announced = false;
  video.addEventListener("playing", () => {
    el.setAttribute("data-started", "");
    setToggle(true);
    if (!announced) {
      announced = true;
      // Hook for the room: load it only after the film has started.
      document.dispatchEvent(new CustomEvent("film:started"));
    }
  });
  video.addEventListener("pause", () => setToggle(false));
  video.addEventListener("ended", () => {
    setToggle(false);
    document.dispatchEvent(new CustomEvent("film:ended"));
  });
  video.addEventListener("timeupdate", showCaption);

  toggle.addEventListener("click", () => {
    if (video.paused) void video.play().catch(() => setToggle(false));
    else video.pause();
  });
  replay.addEventListener("click", () => {
    video.currentTime = 0;
    showCaption();
    void video.play().catch(() => setToggle(false));
  });

  setToggle(false);
  showCaption();
  void video.play().catch(() => setToggle(false));
}
