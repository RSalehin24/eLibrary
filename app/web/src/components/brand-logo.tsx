import { BrandMark } from "./brand-mark";

export function BrandLogo() {
  return <svg className="brand-logo" width="236" height="52" viewBox="0 0 236 52" role="img" aria-label="বাংলা পাঠাগার" lang="bn" focusable="false">
    <BrandMark size={48} />
    <text x="60" y="34" fill="currentColor" fontFamily="var(--font-library), sans-serif" fontSize="24" fontWeight="700">বাংলা পাঠাগার</text>
  </svg>;
}
