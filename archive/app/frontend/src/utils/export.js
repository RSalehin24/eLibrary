export function getExportBlockState({ items, loading, error, nounSingular, nounPlural }) {
  if (error) {
    return { type: "error", message: error };
  }

  if (loading) {
    return {
      type: "info",
      message: `Wait until the ${nounPlural} list finishes loading before exporting.`
    };
  }

  if (!items?.length) {
    return {
      type: "info",
      message: `There are no ${nounPlural} to export.`
    };
  }

  const processingCount = items.filter((item) => item?.state === "processing").length;
  if (processingCount) {
    return {
      type: "info",
      message:
        processingCount === 1
          ? `A ${nounSingular} is still processing. Export after processing finishes.`
          : `${processingCount} ${nounPlural} are still processing. Export after processing finishes.`
    };
  }

  return null;
}
