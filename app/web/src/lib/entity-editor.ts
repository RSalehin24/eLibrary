"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { APIError } from "@/api/http";
import { commandManagedEntity, updateManagedEntity } from "@/api/entities";
import type { EntityUpdate, ManagedEntity } from "@/api/types";
import type { EditorialCommand } from "@/api/editorial";
import type { EntityKind } from "./catalog-entity";
import { useUnsavedChanges } from "./unsaved-changes";

export function useEntityEditor(kind: EntityKind, initialEntity: ManagedEntity) {
  const [entity, setEntity] = useState(initialEntity);
  const [dirty, setDirty] = useState(false);
  const [notice, setNotice] = useState("");
  const router = useRouter();
  const client = useQueryClient();
  async function accept(updated: ManagedEntity) {
    setEntity(updated); setDirty(false); setNotice("পরিবর্তন সংরক্ষিত হয়েছে।");
    await client.invalidateQueries({ queryKey: ["private", "catalog-references"] });
    router.refresh();
  }
  const save = useMutation({ mutationFn: (values: Omit<EntityUpdate, "expected_updated_at">) => updateManagedEntity(kind, entity, values), onSuccess: accept, retry: false });
  const command = useMutation({ mutationFn: (action: EditorialCommand) => commandManagedEntity(kind, entity, action), onSuccess: accept, retry: false });
  const error = save.error ?? command.error;
  const pending = save.isPending || command.isPending;
  const blocked = pending || !!error && (!(error instanceof APIError) || error.status !== 400);
  useUnsavedChanges(dirty || pending);
  return { entity, dirty, notice, save, command, error, blocked, markDirty: () => { setDirty(true); setNotice(""); }, errors: error instanceof APIError ? error.fieldErrors : {} };
}
