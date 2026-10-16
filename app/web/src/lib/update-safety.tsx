"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { UpdateCoordinator, type UpdateParticipant } from "./update-coordinator";

const UpdateContext = createContext<UpdateCoordinator | null>(null);

export function UpdateSafetyProvider({ children }: { children: React.ReactNode }) {
  const [safety] = useState(() => new UpdateCoordinator());
  return <UpdateContext.Provider value={safety}>{children}</UpdateContext.Provider>;
}

export function useUpdateSafety() {
  const safety = useContext(UpdateContext);
  if (!safety) throw new Error("Update safety provider is missing.");
  return safety;
}

export function useUpdateParticipant(participant: UpdateParticipant) {
  const safety = useUpdateSafety();
  useEffect(() => safety.register(participant), [participant, safety]);
}
