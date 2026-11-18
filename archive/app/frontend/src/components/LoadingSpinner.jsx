export default function LoadingSpinner({ size = 16, className = "" }) {
  const classes = ["loading-spinner", className].filter(Boolean).join(" ");

  return <span className={classes} style={{ "--spinner-size": `${size}px` }} aria-hidden="true" />;
}
