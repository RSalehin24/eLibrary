import PageSkeleton from "./PageSkeleton";

export default function PageLoader({
  label = "Loading",
  detail = "",
  className = "",
  variant = "table",
}) {
  const classes = [
    "page-loader",
    `page-loader-variant-${variant}`,
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const screenReaderText = detail ? `${label}. ${detail}` : label;

  return (
    <div
      className={classes}
      role="status"
      aria-live="polite"
      aria-label={screenReaderText}
    >
      <span className="sr-only">{screenReaderText}</span>
      <div className="page-loader-visual" aria-hidden="true">
        <PageSkeleton variant={variant} />
      </div>
    </div>
  );
}
