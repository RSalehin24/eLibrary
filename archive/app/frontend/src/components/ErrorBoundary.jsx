import { Component } from "react";

// Renders a fallback UI if a descendant throws during render. Logs the error
// to the console; preserves the rest of the shell.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    if (typeof console !== "undefined") {
      // eslint-disable-next-line no-console
      console.error("ErrorBoundary caught error:", error, info);
    }
  }

  handleReload = () => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    return (
      <div className="error-boundary" role="alert">
        <div className="error-boundary-card">
          <h1 className="error-boundary-title">Something went wrong</h1>
          <p className="error-boundary-body">
            An unexpected error occurred while rendering this view. You can try
            again or reload the page.
          </p>
          <div className="error-boundary-actions">
            <button
              type="button"
              className="ghost-button"
              onClick={this.handleReset}
            >
              Try again
            </button>
            <button
              type="button"
              className="primary-button"
              onClick={this.handleReload}
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
