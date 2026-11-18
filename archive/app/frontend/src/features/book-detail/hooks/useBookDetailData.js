import { useCallback, useEffect, useMemo, useState } from "react";
import { bookDetailFetch } from "../api";
import { buildBookDetailView } from "../utils";
import { useHtmlPreviewLockState } from "./useHtmlPreviewLockState";

function createInitialEditor() {
  return {
    title: "",
    summary: "",
    contributors: "",
    series: "",
    categories: "",
    notes: "",
  };
}

export function useBookDetailData({
  canEditMetadata,
  location,
  navigate,
  slug,
  toast,
  user,
}) {
  const [book, setBook] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState(() => createInitialEditor());
  const [metadataVersions, setMetadataVersions] = useState([]);
  const [metadataReviews, setMetadataReviews] = useState([]);
  const [reviewForm, setReviewForm] = useState({ state: "pending", notes: "" });
  const [readerState, setReaderState] = useState({
    last_location: "",
    progress_percent: 0,
    last_opened_at: "",
  });
  const [readerAccess, setReaderAccess] = useState(false);
  const [bookmarks, setBookmarks] = useState([]);
  const { htmlPreviewLockedByAssetId, setHtmlPreviewLockedByAssetId } =
    useHtmlPreviewLockState(book);

  const replaceBookRoute = useCallback(
    (nextSlug) => {
      navigate(`/books/${nextSlug}`, {
        replace: true,
        state: location.state,
      });
    },
    [location.state, navigate],
  );

  const applyReaderState = useCallback((sessionPayload) => {
    if (sessionPayload) {
      setReaderAccess(true);
      setReaderState({
        last_location: sessionPayload.last_location || "",
        progress_percent: sessionPayload.progress_percent || 0,
        last_opened_at: sessionPayload.last_opened_at || "",
      });
      return;
    }

    setReaderAccess(false);
    setReaderState({
      last_location: "",
      progress_percent: 0,
      last_opened_at: "",
    });
  }, []);

  const fetchBook = useCallback(
    async (targetSlug = slug) => {
      const payload = await bookDetailFetch(`/catalog/books/${targetSlug}/`);
      setBook(payload);
      setError("");
      if (payload.slug && payload.slug !== targetSlug) {
        replaceBookRoute(payload.slug);
      }
      return payload;
    },
    [replaceBookRoute, slug],
  );

  const refreshMetadataCollections = useCallback(
    async (targetSlug = slug) => {
      if (!canEditMetadata) {
        setMetadataVersions([]);
        setMetadataReviews([]);
        return;
      }

      const [versionsPayload, reviewsPayload] = await Promise.all([
        bookDetailFetch(`/catalog/books/${targetSlug}/metadata-versions/`),
        bookDetailFetch(`/catalog/books/${targetSlug}/metadata-reviews/`),
      ]);
      setMetadataVersions(versionsPayload);
      setMetadataReviews(reviewsPayload);
    },
    [canEditMetadata, slug],
  );

  const fetchReaderCollections = useCallback(
    async (targetSlug = slug) => {
      const [sessionPayload, bookmarkPayload] = await Promise.all([
        bookDetailFetch(`/access/books/${targetSlug}/reading-session/`).catch(
          (nextError) => {
            if ([401, 403].includes(nextError.status)) {
              return null;
            }
            throw nextError;
          },
        ),
        bookDetailFetch(`/access/books/${targetSlug}/bookmarks/`).catch((nextError) => {
          if ([401, 403].includes(nextError.status)) {
            return [];
          }
          throw nextError;
        }),
      ]);

      return { sessionPayload, bookmarkPayload };
    },
    [slug],
  );

  useEffect(() => {
    let active = true;

    async function loadBook() {
      try {
        setLoading(true);
        await fetchBook(slug);
      } catch (nextError) {
        if (active) {
          setError(nextError.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadBook();

    return () => {
      active = false;
    };
  }, [fetchBook, slug]);

  useEffect(() => {
    if (!book) {
      return;
    }
    setEditor({
      title: book.title || "",
      summary: book.summary || "",
      contributors: (book.contributors || [])
        .map((entry) => `${entry.name}|${entry.role}`)
        .join("\n"),
      series: (book.series || []).join(", "),
      categories: (book.categories || []).join(", "),
      notes: "",
    });
  }, [book]);

  useEffect(() => {
    if (!book || !user) {
      setMetadataVersions([]);
      setMetadataReviews([]);
      setBookmarks([]);
      applyReaderState(null);
      return;
    }

    let active = true;

    async function loadSupplementalData() {
      try {
        const requests = [fetchReaderCollections(slug)];

        if (canEditMetadata) {
          requests.push(
            Promise.all([
              bookDetailFetch(`/catalog/books/${slug}/metadata-versions/`).catch(
                (nextError) => {
                  if ([401, 403].includes(nextError.status)) {
                    return [];
                  }
                  throw nextError;
                },
              ),
              bookDetailFetch(`/catalog/books/${slug}/metadata-reviews/`).catch(
                (nextError) => {
                  if ([401, 403].includes(nextError.status)) {
                    return [];
                  }
                  throw nextError;
                },
              ),
            ]),
          );
        }

        const [
          { sessionPayload, bookmarkPayload },
          metadataPayload = [[], []],
        ] = await Promise.all(requests);
        if (!active) {
          return;
        }

        applyReaderState(sessionPayload);
        setBookmarks(bookmarkPayload);
        setMetadataVersions(metadataPayload[0] || []);
        setMetadataReviews(metadataPayload[1] || []);
      } catch (nextError) {
        if (active) {
          toast.error(nextError.message);
        }
      }
    }

    void loadSupplementalData();

    return () => {
      active = false;
    };
  }, [applyReaderState, book, canEditMetadata, fetchReaderCollections, slug, toast, user]);

  useEffect(() => {
    const nextJob = book?.latest_processing_job;
    if (!nextJob || !["queued", "processing"].includes(nextJob.status)) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      fetchBook(slug).catch(() => {});
    }, 4000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [book?.latest_processing_job?.id, book?.latest_processing_job?.status, fetchBook, slug]);

  const detail = useMemo(
    () => buildBookDetailView(book, readerState),
    [book, readerState],
  );
  const bookLinkFilters =
    book?.record_type === "manual" ? { record_type: "manual" } : {};

  return {
    applyReaderState,
    book,
    bookLinkFilters,
    bookmarks,
    detail,
    editor,
    error,
    fetchBook,
    fetchReaderCollections,
    htmlPreviewLockedByAssetId,
    loading,
    metadataReviews,
    metadataVersions,
    readerAccess,
    readerState,
    refreshMetadataCollections,
    replaceBookRoute,
    reviewForm,
    setBookmarks,
    setBook,
    setEditor,
    setHtmlPreviewLockedByAssetId,
    setMetadataReviews,
    setReviewForm,
    slug,
  };
}
