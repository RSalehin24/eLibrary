type Bounds = { left: number; top: number; width: number; height: number };
type NaturalSize = { width: number; height: number };
type ObjectAppearance = { fit: string; position: string };

function objectOffset(position: string, space: number) {
  const keyword = { left: 0, top: 0, center: .5, right: 1, bottom: 1 }[position];
  if (keyword !== undefined) return keyword * space;
  if (/^-?\d+(?:\.\d+)?%$/.test(position)) return Number.parseFloat(position) / 100 * space;
  return /^-?\d+(?:\.\d+)?px$/.test(position) ? Number.parseFloat(position) : null;
}

export function fittedMediaBounds(box: Bounds, natural: NaturalSize, appearance: ObjectAppearance): Bounds | null {
  if (!natural.width || !natural.height || appearance.fit === "fill") return box;
  const contain = Math.min(box.width / natural.width, box.height / natural.height);
  const scale = appearance.fit === "cover" ? Math.max(box.width / natural.width, box.height / natural.height)
    : appearance.fit === "none" ? 1 : appearance.fit === "scale-down" ? Math.min(1, contain) : contain;
  const width = natural.width * scale, height = natural.height * scale;
  const positions = appearance.position.trim().split(/\s+/);
  if (positions.length !== 2) return null;
  const x = objectOffset(positions[0], box.width - width), y = objectOffset(positions[1], box.height - height);
  return x === null || y === null ? null : { left: box.left + x, top: box.top + y, width, height };
}

export function mediaSpatialPoint(element: Element, spatial: { x: number; y: number }) {
  const rectangle = element.getBoundingClientRect();
  const style = element.ownerDocument.defaultView?.getComputedStyle(element);
  const padding = (key: string) => Number.parseFloat(style?.getPropertyValue(key) ?? "0") || 0;
  const left = padding("border-left-width") + padding("padding-left"), top = padding("border-top-width") + padding("padding-top");
  const box = { left: rectangle.left + left, top: rectangle.top + top,
    width: rectangle.width - left - padding("border-right-width") - padding("padding-right"), height: rectangle.height - top - padding("border-bottom-width") - padding("padding-bottom") };
  const media = element as HTMLImageElement & HTMLVideoElement;
  const bounds = fittedMediaBounds(box, { width: media.naturalWidth || media.videoWidth, height: media.naturalHeight || media.videoHeight }, { fit: style?.objectFit ?? "fill", position: style?.objectPosition ?? "50% 50%" });
  if (!bounds) return null;
  const point = { x: bounds.left + bounds.width * spatial.x / 100, y: bounds.top + bounds.height * spatial.y / 100 };
  return point.x < box.left - 1 || point.x > box.left + box.width + 1 || point.y < box.top - 1 || point.y > box.top + box.height + 1 ? null : point;
}
