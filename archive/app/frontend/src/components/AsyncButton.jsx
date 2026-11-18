import LoadingSpinner from "./LoadingSpinner";

export default function AsyncButton({
  children,
  className = "primary-button",
  disabled = false,
  loading = false,
  loadingLabel = "",
  spinnerSize = 16,
  style,
  type = "button",
  ...buttonProps
}) {
  return (
    <button
      {...buttonProps}
      type={type}
      className={className}
      disabled={disabled || loading}
      aria-busy={loading ? "true" : undefined}
      style={{ "--button-spinner-slot-size": `${spinnerSize}px`, ...style }}
    >
      <span className="button-label button-label--stable">
        <span
          className={`button-label-spinner-slot${loading ? " is-visible" : ""}`}
        >
          <LoadingSpinner size={spinnerSize} />
        </span>
        <span className="button-label-text">
          {loading && loadingLabel ? loadingLabel : children}
        </span>
        <span className="button-label-spinner-slot" aria-hidden="true" />
      </span>
    </button>
  );
}
