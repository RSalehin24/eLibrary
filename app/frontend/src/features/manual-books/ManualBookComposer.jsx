import AsyncButton from "../../components/AsyncButton";
import TagInput from "../../components/TagInput";
import { emptyManualBookForm } from "./manualBookFilters";

export function ManualBookComposer({
  categoryOptions,
  contributorOptions,
  seriesOptions,
  form,
  loadingOptions,
  onClose,
  onSubmit,
  setForm,
  submitting,
  titleInputRef
}) {
  return (
    <section
      id="manual-book-composer"
      className="detail-card manual-books-panel manual-book-composer"
    >
      <form className="stack-form manual-book-form" onSubmit={onSubmit}>
        <label>
          <span className="fact-label">Title</span>
          <input
            ref={titleInputRef}
            type="text"
            value={form.title}
            onChange={(event) => setForm({ ...form, title: event.target.value })}
            placeholder="Book title"
            autoComplete="off"
          />
        </label>

        <div className="manual-book-form-grid">
          <TagInput
            label="Writer"
            values={form.writers}
            onChange={(writers) => setForm({ ...form, writers })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Select or create"}
          />
          <TagInput
            label="Translator"
            values={form.translators}
            onChange={(translators) => setForm({ ...form, translators })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <TagInput
            label="Editor"
            values={form.editors}
            onChange={(editors) => setForm({ ...form, editors })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <TagInput
            label="Category"
            values={form.categories}
            onChange={(categories) => setForm({ ...form, categories })}
            suggestions={categoryOptions}
            placeholder={loadingOptions ? "Loading..." : "Select or create"}
          />
        </div>

        <div className="manual-book-form-grid">
          <TagInput
            label="Series"
            values={form.series}
            onChange={(series) => setForm({ ...form, series })}
            suggestions={seriesOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <label>
            <span className="fact-label">Compilation</span>
            <select
              value={form.is_compilation ? "yes" : "no"}
              onChange={(event) =>
                setForm({ ...form, is_compilation: event.target.value === "yes" })
              }
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </label>
          <label>
            <span className="fact-label">Binding</span>
            <select
              value={form.binding}
              onChange={(event) => setForm({ ...form, binding: event.target.value })}
            >
              <option value="">Select</option>
              <option value="hard_cover">Hard Cover</option>
              <option value="paper_back">Paper Back</option>
            </select>
          </label>
          <label>
            <span className="fact-label">Publisher</span>
            <input
              type="text"
              value={form.publisher}
              onChange={(event) => setForm({ ...form, publisher: event.target.value })}
              placeholder="Optional"
              autoComplete="off"
            />
          </label>
        </div>

        <div className="manual-book-form-grid">
          <label>
            <span className="fact-label">Price</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.price}
              onChange={(event) => setForm({ ...form, price: event.target.value })}
              placeholder="Optional"
            />
          </label>
          <label className="manual-book-form-span-3">
            <span className="fact-label">Summary</span>
            <textarea
              value={form.summary}
              onChange={(event) => setForm({ ...form, summary: event.target.value })}
              placeholder="Optional"
            />
          </label>
        </div>

        <div className="inline-pills manual-book-form-actions">
          <AsyncButton type="submit" className="primary-button" loading={submitting} loadingLabel="Adding..." spinnerSize={14}>
            Add & next
          </AsyncButton>
          <button
            type="button"
            className="ghost-button"
            onClick={() => setForm(emptyManualBookForm)}
            disabled={submitting}
          >
            Clear fields
          </button>
          <button type="button" className="ghost-button" onClick={onClose} disabled={submitting}>
            Done
          </button>
        </div>
      </form>
    </section>
  );
}
