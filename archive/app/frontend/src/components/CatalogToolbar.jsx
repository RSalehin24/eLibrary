import LoadingSpinner from "./LoadingSpinner";
import { renderField } from "./catalog-toolbar/fields.jsx";
import { CatalogSearchRow } from "./catalog-toolbar/SearchRow";

export { CatalogSearchRow } from "./catalog-toolbar/SearchRow";

export default function CatalogToolbar({
  filters,
  setFilters,
  fields,
  defaultFilters,
  filtersExpanded,
  setFiltersExpanded,
  onSubmit,
  onReset,
  searchPlaceholder,
  resultCount,
  resultCountLoading = false,
  secondaryContent = null,
  submitLabel = "Apply filters",
  inline = false,
  drawerId = "catalog-filter-drawer",
  showSearchRow = true,
  searchRowCompact = false,
  searchRowClassName = "",
  onSearchClear = null,
  showResultCount = true,
  buttonsDisabled = false,
  bare = false,
  searchActionsExtra = null,
  secondaryBelow = false,
  buttonsLoading = false,
  drawerFirst = false,
  sortValue = "",
  sortOptions = [],
  onSortChange = null,
  sortAriaLabel = "Sort results",
  sortDisabled = false,
}) {
  const wrapperClassName = `catalog-toolbar-wrap${filtersExpanded ? " is-expanded" : ""}${inline ? " is-inline" : ""}${
    bare ? " is-bare" : ""
  }`;
  const hasInlineSecondary = Boolean(secondaryContent && !secondaryBelow);
  const hasSplitTopline = showSearchRow && hasInlineSecondary;
  const hasSecondaryOnlyTopline = !showSearchRow && hasInlineSecondary;
  const toplineClassName = `catalog-toolbar-topline${hasSplitTopline ? " has-secondary" : ""}${
    hasSecondaryOnlyTopline ? " is-secondary-only" : ""
  }${bare ? " is-bare" : ""}`;
  const handleSubmit = (event, submittedFilters = null) => {
    if (!onSubmit) {
      return;
    }

    if (submittedFilters) {
      onSubmit(event, submittedFilters);
      return;
    }

    const queryInput = event.currentTarget?.querySelector('input[type="search"]');
    onSubmit(event, {
      ...filters,
      q: queryInput ? queryInput.value : filters.q,
    });
  };
  const searchRow = showSearchRow ? (
    <CatalogSearchRow
      filters={filters}
      setFilters={setFilters}
      fields={fields}
      defaultFilters={defaultFilters}
      filtersExpanded={filtersExpanded}
      setFiltersExpanded={setFiltersExpanded}
      searchPlaceholder={searchPlaceholder}
      resultCount={resultCount}
      resultCountLoading={resultCountLoading}
      drawerId={drawerId}
      compact={searchRowCompact}
      className={searchRowClassName}
      onSearchClear={onSearchClear}
      onSearchSubmit={handleSubmit}
      showResultCount={showResultCount}
      buttonsDisabled={buttonsDisabled}
      actionsExtra={searchActionsExtra}
      sortValue={sortValue}
      sortOptions={sortOptions}
      onSortChange={onSortChange}
      sortAriaLabel={sortAriaLabel}
      sortDisabled={sortDisabled}
    />
  ) : null;
  const secondaryShellClassName = `catalog-toolbar-secondary-shell${hasSecondaryOnlyTopline ? " is-standalone" : ""}${
    bare ? " is-bare" : ""
  }${secondaryBelow ? " is-below" : ""}`;
  const filterDrawer = (
    <div
      id={drawerId}
      className={`catalog-filter-drawer${filtersExpanded ? " is-open" : ""}`}
      aria-hidden={filtersExpanded ? "false" : "true"}
    >
      <div className="catalog-filter-grid">
        {fields.map((field) => (
          <label key={field.key} className="catalog-filter-field">
            <span className="fact-label">{field.label}</span>
            {renderField(field, filters, setFilters)}
          </label>
        ))}
      </div>
      <div className="catalog-filter-actions">
        <button
          type="submit"
          className="primary-button"
          disabled={buttonsDisabled || buttonsLoading}
        >
          <span className="button-label">
            {buttonsLoading ? <LoadingSpinner size={14} /> : null}
            {submitLabel}
          </span>
        </button>
        <button
          type="button"
          className="ghost-button"
          onClick={onReset}
          disabled={buttonsDisabled}
        >
          Reset
        </button>
      </div>
    </div>
  );

  return (
    <section className={wrapperClassName}>
      <div className="catalog-toolbar-surface">
        <form className="catalog-toolbar-form" onSubmit={handleSubmit}>
          {drawerFirst ? filterDrawer : null}
          {searchRow || hasInlineSecondary ? (
            <div className={toplineClassName}>
              {searchRow ? (
                hasInlineSecondary ? (
                  <div
                    className={`catalog-toolbar-primary${bare ? " is-bare" : ""}`}
                  >
                    {searchRow}
                  </div>
                ) : (
                  searchRow
                )
              ) : null}
              {hasInlineSecondary ? (
                <div className={secondaryShellClassName}>
                  {secondaryContent}
                </div>
              ) : null}
            </div>
          ) : null}
          {secondaryContent && secondaryBelow ? (
            <div className={secondaryShellClassName}>{secondaryContent}</div>
          ) : null}
          {!drawerFirst ? filterDrawer : null}
        </form>
      </div>
    </section>
  );
}
