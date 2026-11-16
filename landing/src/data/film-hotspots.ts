// Room hotspots for /film/ (frozen spec R-17). x and y are percentages of the
// full source image: 1920x1080 for landscape, 1080x1920 for portrait. The phone
// crop math and the pairwise distances are in components/film/ROOM-GEOMETRY.md.

export interface Hotspot {
  n: number;
  target: string;
  section: string;
  label: string;
  land: { x: number; y: number };
  port: { x: number; y: number };
}

export const ROOM_BREAKPOINT = 720;

export const roomImage = {
  land: { src: "/film/room-land.jpg", width: 1920, height: 1080 },
  port: { src: "/film/room-port.jpg", width: 1080, height: 1920 },
  alt: "The table in a dim room at night: sealed notes, assistants as pawns, a result card, a receipt, an install card, a book and a status plaque",
} as const;

export const roomHint = "Seven things in this room open six sections.";

export const hotspots: Hotspot[] = [
  {
    n: 1,
    target: "how-1",
    section: "How it works, step 1",
    label: "Three sealed notes",
    land: { x: 61.2, y: 63.1 },
    port: { x: 62.5, y: 61.6 },
  },
  {
    n: 2,
    target: "how-2",
    section: "How it works, step 2",
    label: "Bob's assistant",
    land: { x: 51.3, y: 61.1 },
    port: { x: 51.4, y: 60.8 },
  },
  {
    n: 3,
    target: "code",
    section: "The dinner in code",
    label: "Result card",
    land: { x: 25, y: 79.6 },
    port: { x: 16.7, y: 71.4 },
  },
  {
    n: 4,
    target: "receipt",
    section: "The receipt",
    label: "Receipt",
    land: { x: 75, y: 79.6 },
    port: { x: 81.5, y: 72.9 },
  },
  {
    n: 5,
    target: "install",
    section: "Install",
    label: "Install card",
    land: { x: 52.1, y: 88.4 },
    port: { x: 53.2, y: 78.1 },
  },
  {
    n: 6,
    target: "docs",
    section: "Docs and GitHub",
    label: "Book",
    land: { x: 50.8, y: 75.2 },
    port: { x: 52.3, y: 68.6 },
  },
  {
    n: 7,
    target: "status",
    section: "Status",
    label: "Plaque",
    land: { x: 42.2, y: 69.6 },
    port: { x: 40, y: 65.1 },
  },
];
