import { ImageResponse } from "next/og";
import { BrandMark } from "@/components/brand-mark";

export function brandIcon(size: number) {
  return new ImageResponse(<div style={{ display: "flex", width: "100%", height: "100%", alignItems: "center", justifyContent: "center", background: "#173e35" }}>
    <BrandMark size={size * .8} />
  </div>, { width: size, height: size, headers: { "Cache-Control": "public, max-age=31536000, immutable" } });
}
