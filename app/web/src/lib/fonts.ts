import localFont from "next/font/local";

export const libraryFont = localFont({
  src: [
    { path: "../assets/fonts/NotoSansBengali-Regular.ttf", weight: "400", style: "normal" },
    { path: "../assets/fonts/NotoSansBengali-Bold.ttf", weight: "700", style: "normal" },
  ],
  variable: "--font-library", display: "swap",
});
