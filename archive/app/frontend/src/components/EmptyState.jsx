export default function EmptyState({ title, body, actions = null }) {
  return (
    <div className="empty-state" role="status">
      <h3>{title}</h3>
      {body ? <p>{body}</p> : null}
      {actions ? (
        <div className="empty-state-actions inline-pills">{actions}</div>
      ) : null}
    </div>
  );
}
