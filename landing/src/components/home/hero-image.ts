// One place builds the hero sources, so the <picture> and its preload links name the same files.
// Widths stop at the masters' own size (1920 landscape, 1080 portrait): no upscaled entries.
import { getImage } from "astro:assets";
import land from "../../assets/home/hero-land.jpg";
import port from "../../assets/home/hero-port.jpg";

export const PORTRAIT_MEDIA = "(max-width: 720px)";
export const LANDSCAPE_MEDIA = "(min-width: 721px)";
export const SIZES = "100vw";

const FORMATS = ["avif", "webp", "jpeg"] as const;

async function set(src: ImageMetadata, widths: number[]) {
  const [avif, webp, jpeg] = await Promise.all(
    FORMATS.map((format) => getImage({ src, widths, format, quality: 60 })),
  );
  return {
    width: src.width,
    height: src.height,
    avif: avif.srcSet.attribute,
    webp: webp.srcSet.attribute,
    jpeg: jpeg.srcSet.attribute,
    fallback: jpeg.src,
  };
}

export async function heroSources() {
  const [landscape, portrait] = await Promise.all([set(land, [1280, 1920]), set(port, [828, 1080])]);
  return { landscape, portrait };
}
