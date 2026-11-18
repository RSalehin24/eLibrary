import { NavLink } from "react-router-dom";

function Caret({ open }) {
  return (
    <span
      className={open ? "nav-dropdown-caret is-open" : "nav-dropdown-caret"}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 16 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m3.5 6 4.5 4 4.5-4" />
      </svg>
    </span>
  );
}

export default function NavDropdown({
  menuRef,
  active,
  open,
  label,
  items,
  onToggle,
  onItemClick,
}) {
  return (
    <div ref={menuRef} className="nav-dropdown-shell">
      <button
        type="button"
        className={
          active
            ? "nav-link is-active nav-dropdown-trigger"
            : "nav-link nav-dropdown-trigger"
        }
        onClick={onToggle}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <span>{label}</span>
        <Caret open={open} />
      </button>
      {open ? (
        <div className="nav-dropdown-panel" role="menu">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-dropdown-link is-active" : "nav-dropdown-link"
              }
              onClick={onItemClick}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      ) : null}
    </div>
  );
}
