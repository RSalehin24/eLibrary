import { Link, useLocation } from "react-router-dom";

export function getCurrentRoutePath(location) {
  return `${location.pathname}${location.search}${location.hash}`;
}

export function getBookReturnTarget(location, fallback = "/library") {
  const from = location.state?.from;
  if (typeof from === "string" && from.startsWith("/")) {
    return from;
  }
  return fallback;
}

export default function BookRouteLink({
  slug,
  to,
  state,
  children,
  ...props
}) {
  const location = useLocation();
  const nextState = {
    ...state,
    from:
      typeof state?.from === "string"
        ? state.from
        : getCurrentRoutePath(location),
  };

  return (
    <Link to={to || `/books/${slug}`} state={nextState} {...props}>
      {children}
    </Link>
  );
}
