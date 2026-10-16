import { ImageResponse } from "next/og";

export function appIcon(size: number) {
  return new ImageResponse(<div style={{ display: "flex", width: "100%", height: "100%", alignItems: "center", justifyContent: "center", background: "#173e35" }}>
    <svg width={size * .64} height={size * .64} viewBox="0 0 100 100"><path fill="#fbfaf6" d="M12 24 Q30 15 48 25 L48 78 Q30 68 12 77 Z M52 25 Q70 15 88 24 L88 77 Q70 68 52 78 Z" /><path stroke="#cfa565" strokeWidth="4" fill="none" d="M22 34 Q32 29 40 34 M22 45 Q32 40 40 45 M22 56 Q32 51 40 56 M60 34 Q70 29 78 34 M60 45 Q70 40 78 45 M60 56 Q70 51 78 56" /></svg>
  </div>, { width: size, height: size, headers: { "Cache-Control": "public, max-age=31536000, immutable" } });
}
