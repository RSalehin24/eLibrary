import { getStatusMeta } from "../utils/bookPresentation";

export default function StatusPill({ value }) {
  const meta = getStatusMeta(value);
  return (
    <span className={`status-pill status-${value || "unknown"}`} title={meta.description || meta.label}>
      {meta.label}
    </span>
  );
}
