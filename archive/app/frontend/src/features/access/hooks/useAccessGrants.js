import { useMemo, useState } from "react";
import { accessFetch } from "../api";
import { initialGrantForm } from "../constants";
import { grantTargetField, sortValues } from "../utils";

export function useAccessGrants({
  loadAdminData,
  references,
  scopedGrants,
  scopeLabelMap,
  toast,
  userId,
}) {
  const [submittingGrant, setSubmittingGrant] = useState(false);
  const [deletingGrantId, setDeletingGrantId] = useState(null);
  const [grantForm, setGrantForm] = useState(initialGrantForm);
  const [targetSearch, setTargetSearch] = useState("");

  function resetGrantForm() {
    setGrantForm(initialGrantForm);
    setTargetSearch("");
  }

  const targetOptions = useMemo(() => {
    if (grantForm.targetType === "category") {
      return references.categories.map((entry) => ({
        id: entry.id,
        label: entry.name,
      }));
    }
    if (grantForm.targetType === "writer") {
      return references.writers.map((entry) => ({
        id: entry.id,
        label: entry.name,
      }));
    }
    return references.books.map((entry) => ({
      id: entry.id,
      label: entry.title,
    }));
  }, [
    grantForm.targetType,
    references.books,
    references.categories,
    references.writers,
  ]);

  const filteredTargetOptions = useMemo(() => {
    const query = targetSearch.trim().toLowerCase();
    if (!query) {
      return targetOptions;
    }
    return targetOptions.filter((entry) =>
      entry.label.toLowerCase().includes(query),
    );
  }, [targetOptions, targetSearch]);

  function toggleGrantScope(scopeValue) {
    setGrantForm((current) => {
      let nextScopes = current.scopes.includes(scopeValue)
        ? current.scopes.filter((value) => value !== scopeValue)
        : [...current.scopes, scopeValue];
      if (scopeValue === "read:once" && nextScopes.includes("read:once")) {
        nextScopes = nextScopes.filter((value) => value !== "read:durable");
      } else if (scopeValue === "read:durable" && nextScopes.includes("read:durable")) {
        nextScopes = nextScopes.filter((value) => value !== "read:once");
      }
      return {
        ...current,
        scopes: sortValues(nextScopes),
      };
    });
  }

  function toggleGrantTarget(targetId) {
    setGrantForm((current) => {
      const nextTargets = current.targetIds.includes(targetId)
        ? current.targetIds.filter((value) => value !== targetId)
        : [...current.targetIds, targetId];
      return {
        ...current,
        targetIds: sortValues(nextTargets),
      };
    });
  }

  function switchTargetType(targetType) {
    setGrantForm((current) => ({
      ...current,
      targetType,
      targetIds: [],
    }));
    setTargetSearch("");
  }

  async function submitGrant(event) {
    event.preventDefault();
    if (submittingGrant) {
      return;
    }

    if (!grantForm.user) {
      toast.error("Select a user first.");
      return;
    }
    if (!grantForm.scopes.length) {
      toast.error("Select at least one permission.");
      return;
    }
    if (!grantForm.targetIds.length) {
      toast.error("Select at least one target.");
      return;
    }

    const targetField = grantTargetField(grantForm.targetType);
    const existingGrantKeys = new Set(
      scopedGrants
        .filter((grant) => `${grant.user}` === `${grantForm.user}`)
        .map((grant) => `${grant.scope}:${grant[targetField]}`),
    );

    const requests = [];
    let skippedCount = 0;
    for (const scope of grantForm.scopes) {
      for (const targetId of grantForm.targetIds) {
        const key = `${scope}:${targetId}`;
        if (existingGrantKeys.has(key)) {
          skippedCount += 1;
          continue;
        }
        requests.push(
          accessFetch("/access/grants/", {
            method: "POST",
            body: {
              user: grantForm.user,
              scope,
              [targetField]: targetId,
              expires_at: null,
              notes: "",
            },
          }),
        );
      }
    }

    if (!requests.length) {
      toast.error("These access rules already exist.");
      return;
    }

    try {
      setSubmittingGrant(true);
      await Promise.all(requests);
      resetGrantForm();
      toast.success(
        skippedCount
          ? `Access updated. Skipped ${skippedCount} existing rule${skippedCount === 1 ? "" : "s"}.`
          : "Access updated.",
      );
      await loadAdminData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSubmittingGrant(false);
    }
  }

  async function deleteGrant(grant) {
    if (deletingGrantId) {
      return;
    }
    if (
      !window.confirm(
        `Remove ${scopeLabelMap.get(grant.scope) || grant.scope} from ${grant.user_email}?`,
      )
    ) {
      return;
    }

    try {
      setDeletingGrantId(grant.id);
      await accessFetch(`/access/grants/${grant.id}/`, { method: "DELETE" });
      toast.success("Access removed.");
      await loadAdminData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setDeletingGrantId(null);
    }
  }

  return {
    deleteGrant,
    deletingGrantId,
    filteredTargetOptions,
    grantForm,
    resetGrantForm,
    scopedGrants,
    setGrantForm,
    setTargetSearch,
    submitGrant,
    submittingGrant,
    switchTargetType,
    targetSearch,
    toggleGrantScope,
    toggleGrantTarget,
    userId,
  };
}
