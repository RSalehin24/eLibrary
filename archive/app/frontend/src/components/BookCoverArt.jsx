import { useState } from "react";
import { resolveAppUrl } from "../api/client";
import { getPrimaryContributorName } from "../utils/bookPresentation";

export default function BookCoverArt({ book, className = "", ariaHidden = false }) {
  const [imageError, setImageError] = useState(false);
  const coverUrl = resolveAppUrl(book.cover_download_url);
  const hasCover = Boolean(coverUrl) && !imageError;
  const authorName = getPrimaryContributorName(book);
  const classes = ["book-cover-surface", className].filter(Boolean).join(" ");

  if (hasCover) {
    return (
      <div className={`${classes} book-cover-media`} aria-hidden={ariaHidden}>
        <img
          className="book-cover-image"
          src={coverUrl}
          alt={ariaHidden ? "" : `${book.title} cover`}
          loading="lazy"
          decoding="async"
          onError={() => setImageError(true)}
        />
      </div>
    );
  }

  return (
    <div className={`${classes} book-cover-placeholder`} aria-hidden={ariaHidden}>
      <strong>{book.title}</strong>
      <p>{authorName || "Cover unavailable"}</p>
    </div>
  );
}
