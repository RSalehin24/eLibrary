const STRUCTURAL_TAGS = new Set(["div", "main", "section", "article"]);
const IGNORED_CANDIDATE_TAGS = new Set(["script", "style", "link", "meta"]);

function getNodeTextLength(node) {
  return (node?.textContent || "").trim().length;
}

function findLargestStructuralCandidate(body) {
  const candidateElements = Array.from(body.children || []).filter((element) => {
    if (!element || element.nodeType !== 1) return false;
    return !IGNORED_CANDIDATE_TAGS.has((element.tagName || "").toLowerCase());
  });

  return candidateElements
    .filter((element) => STRUCTURAL_TAGS.has((element.tagName || "").toLowerCase()))
    .reduce((largest, element) => {
      if (!largest) return element;
      return getNodeTextLength(element) > getNodeTextLength(largest) ? element : largest;
    }, null);
}

function findNextScrollContainer(body) {
  const largestCandidate = findLargestStructuralCandidate(body);
  const bodyTextLength = getNodeTextLength(body);
  const largestCandidateTextLength = getNodeTextLength(largestCandidate);
  const largestCandidateCoverage =
    bodyTextLength > 0 ? largestCandidateTextLength / bodyTextLength : 0;
  const bodyCanScroll = body.scrollHeight > body.clientHeight + 1;

  if (
    !bodyCanScroll &&
    largestCandidate &&
    largestCandidateTextLength > 180 &&
    largestCandidateCoverage > 0.5
  ) {
    return largestCandidate;
  }

  return null;
}

export function syncReaderScrollContainer({ body, doc, isDocumentUsable }) {
  const nextScrollContainer = findNextScrollContainer(body);

  if (
    doc.__readerScrollContainer &&
    doc.__readerScrollContainer !== nextScrollContainer &&
    doc.__readerScrollContainer.classList
  ) {
    doc.__readerScrollContainer.classList.remove("reader-scroll-container");
  }

  if (!nextScrollContainer?.classList) {
    body.classList.remove("reader-scroll-host");
    doc.__readerScrollContainer = null;
    return;
  }

  nextScrollContainer.classList.add("reader-scroll-container");
  body.classList.add("reader-scroll-host");
  doc.__readerScrollContainer = nextScrollContainer;

  const validateScrollContainer = () => {
    if (!isDocumentUsable(doc)) return;

    const currentContainer = doc.__readerScrollContainer;
    if (!currentContainer || !body?.classList) return;

    const containerCanScroll =
      currentContainer.scrollHeight > currentContainer.clientHeight + 1;
    if (containerCanScroll) return;

    currentContainer.classList.remove("reader-scroll-container");
    body.classList.remove("reader-scroll-host");
    doc.__readerScrollContainer = null;
  };

  requestAnimationFrame(() => {
    validateScrollContainer();
    requestAnimationFrame(validateScrollContainer);
  });
}
