export default function PhysicalBookSpecifications({ book }) {
  return (
<section className="detail-card physical-book-specs-card">
        <div className="section-title-block">
          <p className="eyebrow">Specifications</p>
          <h2>Physical Book Details</h2>
        </div>
        <div className="physical-specs-grid">
          <div className="spec-item">
            <span className="spec-label">Publisher</span>
            <span className="spec-value">{book.publisher || "Not specified"}</span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Binding</span>
            <span className="spec-value">
              {book.binding === "hard_cover"
                ? "Hard Cover"
                : book.binding === "paper_back"
                  ? "Paper Back"
                  : book.binding || "Not specified"}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Price</span>
            <span className="spec-value">
              {book.price ? `৳ ${parseFloat(book.price).toFixed(2)}` : "Not specified"}
            </span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Compilation</span>
            <span className="spec-value">{book.is_compilation ? "Yes" : "No"}</span>
          </div>
          <div className="spec-item">
            <span className="spec-label">Language</span>
            <span className="spec-value">{book.language === "en" ? "English" : "বাংলা"}</span>
          </div>
        </div>
      </section>
  );
}
