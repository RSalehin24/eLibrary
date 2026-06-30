import { useRef } from "react";
import AsyncButton from "../../components/AsyncButton";
import TagInput from "../../components/TagInput";
import { emptyManualBookForm } from "./manualBookFilters";

export function ManualBookComposer({
  categoryOptions,
  contributorOptions,
  seriesOptions,
  publisherOptions,
  form,
  loadingOptions,
  onClose,
  onSubmit,
  setForm,
  submitting,
  titleInputRef,
  isEditing = false
}) {
  // Refs for every TagInput field (expose focus() + contains() via imperative handle)
  const writerRef = useRef(null);
  const translatorRef = useRef(null);
  const editorRef = useRef(null);
  const categoryRef = useRef(null);
  const seriesRef = useRef(null);
  const publisherRef = useRef(null);

  // Refs for plain DOM fields
  const compilationRef = useRef(null);
  const bindingRef = useRef(null);
  const priceRef = useRef(null);
  const languageRef = useRef(null);
  const summaryRef = useRef(null);

  /**
   * Ordered navigation sequence for Cmd/Ctrl + Arrow field jumping.
   * Each entry is either:
   *   { type: "dom",        ref }  — plain input / select / textarea
   *   { type: "imperative", ref }  — TagInput with focus() + contains()
   */
  const fieldSequence = [
    { type: "dom",        ref: titleInputRef },
    { type: "imperative", ref: writerRef },
    { type: "imperative", ref: translatorRef },
    { type: "imperative", ref: editorRef },
    { type: "imperative", ref: categoryRef },
    { type: "imperative", ref: seriesRef },
    { type: "dom",        ref: compilationRef },
    { type: "dom",        ref: bindingRef },
    { type: "imperative", ref: publisherRef },
    { type: "dom",        ref: priceRef },
    { type: "dom",        ref: languageRef },
    { type: "dom",        ref: summaryRef },
  ];

  function handleFormKeyDown(event) {
    // Cmd+Arrow (Mac) or Ctrl+Arrow (Windows/Linux)
    const modifier = event.metaKey || event.ctrlKey;
    if (!modifier) return;
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;

    const activeEl = document.activeElement;
    const direction = event.key === "ArrowRight" ? 1 : -1;

    // Find which field currently has focus
    let currentIndex = -1;
    for (let i = 0; i < fieldSequence.length; i++) {
      const { type, ref } = fieldSequence[i];
      if (!ref.current) continue;
      const matches =
        type === "imperative"
          ? ref.current.contains(activeEl)
          : ref.current === activeEl;
      if (matches) { currentIndex = i; break; }
    }

    if (currentIndex === -1) return; // focus is outside the form fields

    const nextIndex = currentIndex + direction;
    if (nextIndex < 0 || nextIndex >= fieldSequence.length) return;

    event.preventDefault(); // prevent native Cmd/Ctrl+Arrow cursor jump

    const next = fieldSequence[nextIndex];
    next.ref.current?.focus();
  }

  return (
    <section
      id="manual-book-composer"
      className="detail-card manual-books-panel manual-book-composer"
    >
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
      <form
        className="stack-form manual-book-form"
        onSubmit={onSubmit}
        onKeyDown={handleFormKeyDown}
      >
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
            ref={writerRef}
            label="Writer"
            values={form.writers}
            onChange={(writers) => setForm({ ...form, writers })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <TagInput
            ref={translatorRef}
            label="Translator"
            values={form.translators}
            onChange={(translators) => setForm({ ...form, translators })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <TagInput
            ref={editorRef}
            label="Editor"
            values={form.editors}
            onChange={(editors) => setForm({ ...form, editors })}
            suggestions={contributorOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <TagInput
            ref={categoryRef}
            label="Category"
            values={form.categories}
            onChange={(categories) => setForm({ ...form, categories })}
            suggestions={categoryOptions}
            placeholder={loadingOptions ? "Loading..." : "Select or create"}
          />
        </div>

        <div className="manual-book-form-grid">
          <TagInput
            ref={seriesRef}
            label="Series"
            values={form.series}
            onChange={(series) => setForm({ ...form, series })}
            suggestions={seriesOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
          <label>
            <span className="fact-label">Compilation</span>
            <select
              ref={compilationRef}
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
              ref={bindingRef}
              value={form.binding}
              onChange={(event) => setForm({ ...form, binding: event.target.value })}
            >
              <option value="">Select</option>
              <option value="hard_cover">Hard Cover</option>
              <option value="paper_back">Paper Back</option>
            </select>
          </label>
          <TagInput
            ref={publisherRef}
            label="Publisher"
            values={form.publisher ? [form.publisher] : []}
            onChange={(publishers) =>
              setForm({ ...form, publisher: publishers[publishers.length - 1] || "" })
            }
            suggestions={publisherOptions}
            placeholder={loadingOptions ? "Loading..." : "Optional"}
          />
        </div>

         <div className="manual-book-form-grid">
          <label>
            <span className="fact-label">Price</span>
            <input
              ref={priceRef}
              type="number"
              min="0"
              step="0.01"
              value={form.price}
              onChange={(event) => setForm({ ...form, price: event.target.value })}
              placeholder="Optional"
            />
          </label>
          <label>
            <span className="fact-label">Language</span>
            <select
              ref={languageRef}
              value={form.language || "bn"}
              onChange={(event) => setForm({ ...form, language: event.target.value })}
            >
              <option value="bn">বাংলা</option>
              <option value="en">English</option>
            </select>
          </label>
          <label className="manual-book-form-span-2">
            <span className="fact-label">Summary</span>
            <textarea
              ref={summaryRef}
              value={form.summary}
              onChange={(event) => setForm({ ...form, summary: event.target.value })}
              placeholder="Optional"
            />
          </label>
        </div>

        <div className="inline-pills manual-book-form-actions">
          <AsyncButton
            type="submit"
            className="primary-button"
            loading={submitting}
            loadingLabel={isEditing ? "Saving..." : "Adding..."}
            spinnerSize={14}
          >
            {isEditing ? "Save" : "Add & next"}
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
