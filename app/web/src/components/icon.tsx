const paths = {
  check: "M20 6L9 17l-5-5",
  settings: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
  fullscreen: "M3 9V3h6 M15 3h6v6 M21 15v6h-6 M9 21H3v-6",
  warning: "M12 8v5 M12 17h.01 M12 2L1 21h22z",
  overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  books: "M3 4h5v16H3z M8 4h5v16H8z M15 5l4-1 4 15-4 1z",
  read: "M12 5v15 M3 4c3-1 6 0 9 2 3-2 6-3 9-2v15c-3-1-6 0-9 2-3-2-6-3-9-2z",
  source: "M9 3H4v18h16V8z M9 3v5h11 M8 12h8 M8 16h5",
  people: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M16 4a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-4 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
  tags: "M20 13l-7 7-10-10V3h7z M7 7h.01",
  jobs: "M8 3H4v18h16V3h-4 M8 2h8v4H8z M8 11h8 M8 16h5",
  schedule: "M8 2v4 M16 2v4 M3 10h18 M3 4h18v18H3z M8 14h3v3H8z",
  arrow: "M4 12h16 M14 6l6 6-6 6",
  external: "M14 3h7v7 M21 3l-10 10 M10 3H3v18h18v-7",
  search: "M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  download: "M12 3v12 M7 10l5 5 5-5 M4 15v6h16v-6",
  upload: "M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6",
  plus: "M12 5v14 M5 12h14",
  send: "M22 2L9 15 M22 2l-7 20-6-7-7-6z",
  refresh: "M20 7v5h-5 M4 17v-5h5 M6 7a7 7 0 0 1 12-2l2 2 M18 17a7 7 0 0 1-12 2l-2-2",
  trash: "M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7",
  notes: "M4 3h12l4 4v14H4z M15 3v5h5 M8 12h8 M8 16h6",
  bookmark: "M6 3h12v18l-6-4-6 4z",
  edit: "M12 20h9 M16 3l5 5L8 21H3v-5z M14 5l5 5",
  save: "M4 3h13l4 4v14H3V3z M7 3v6h10V3 M7 21v-8h10v8",
  logout: "M9 3H3v18h6 M9 12h12 M16 7l5 5-5 5",
  help: "M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4 M12 17h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
} as const;

export type IconName = keyof typeof paths;
export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>;
}
