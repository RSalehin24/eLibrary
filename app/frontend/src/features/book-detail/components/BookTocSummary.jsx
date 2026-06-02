function tocLabel(entry, fallbackLabel) {
  return entry?.title || entry?.label || fallbackLabel;
}

function tocContentPill(hasContent) {
  if (hasContent === true) {
    return <span className="status-pill status-ready">Content ready</span>;
  }
  if (hasContent === null) {
    return (
      <span className="status-pill status-needs_review">
        No content on source
      </span>
    );
  }
  if (hasContent === false) {
    return <span className="status-pill status-needs_review">TOC only</span>;
  }
  return null;
}

function TocBranch({ entries, path = "toc" }) {
  if (!entries?.length) {
    return null;
  }

  return (
    <div className="toc-record-list">
      {entries.map((entry, index) => {
        const itemKey = `${path}-${index}`;
        const children = Array.isArray(entry?.children) ? entry.children : [];
        const label = tocLabel(entry, `Section ${index + 1}`);
        const hasContentDefined = entry != null && "has_content" in entry;

        return (
          <article
            key={itemKey}
            className={`toc-record-card${children.length ? "" : " toc-record-card--empty"}`}
          >
            <div className="toc-record-copy">
              <strong>{label}</strong>
              {entry?.type || hasContentDefined ? (
                <div className="inline-pills toc-record-pills">
                  {entry?.type ? (
                    <span className="status-pill">{entry.type}</span>
                  ) : null}
                  {hasContentDefined ? tocContentPill(entry.has_content) : null}
                </div>
              ) : null}
            </div>
            {children.length ? (
              <div className="toc-record-content">
                <TocBranch entries={children} path={itemKey} />
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

export default function BookTocSummary({ toc }) {
  return <TocBranch entries={toc} />;
}
