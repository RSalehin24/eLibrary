import { notFound } from "next/navigation";
import { entityLabels, type EntityKind } from "./catalog-entity";

export function managedEntityKind(value: string): EntityKind {
  if (!Object.hasOwn(entityLabels, value)) notFound();
  return value as EntityKind;
}

