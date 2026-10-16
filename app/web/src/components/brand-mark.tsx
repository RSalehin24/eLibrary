export function BrandMark({ size = 48 }: { size?: number }) {
  return <svg className="brand-mark" width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true" focusable="false">
    <rect width="64" height="64" rx="18" fill="#173e35" />
    <path d="M13 19c7-2 13 0 19 4v27c-6-4-12-6-19-4V19Z" fill="#fff9ed" />
    <path d="M51 19c-7-2-13 0-19 4v27c6-4 12-6 19-4V19Z" fill="#f1e4c7" />
    <path d="M32 24v25M19 27c3 0 5 1 8 2M19 34c3 0 5 1 8 2M37 29c3-1 5-2 8-2M37 36c3-1 5-2 8-2" stroke="#173e35" strokeWidth="1.6" strokeLinecap="round" />
    <path d="M40 14v12l4-3 4 3V14h-8Z" fill="#c49a5a" />
  </svg>;
}
