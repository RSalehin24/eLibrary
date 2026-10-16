import { AdminText } from "@/components/admin-language";
import type { ManagedEntity } from "@/api/types";
import type { EntityKind } from "@/lib/catalog-entity";
import type { EditorialValues } from "@/lib/editorial-fields";
import { EditorialField } from "./editorial-field";
import { EditorialSEOFields, EditorialTextFields } from "./editorial-metadata-fields";
import { CatalogReferenceSelector } from "./catalog-reference-selector";

type EntityFieldProps = { kind: EntityKind; entity: EditorialValues & Pick<ManagedEntity, "name" | "selected_books">; disabled: boolean; errors: Record<string, string[]>; onChange: () => void };

export function EntityFields({ kind, entity, disabled, errors, onChange }: EntityFieldProps) {
  return <><fieldset disabled={disabled}><legend><AdminText>{"পরিচিতি ও সম্পাদকীয় তথ্য"}</AdminText></legend>
    <EditorialField name="name" label="নাম" value={entity.name} maxLength={255} errors={errors.name} />
    <EditorialTextFields values={entity} errors={errors} />
  </fieldset>
    {kind === "collections" && <CatalogReferenceSelector kind="books" label="নির্বাচিত বই" name="book_ids" initialSelection={entity.selected_books} disabled={disabled} errors={errors.book_ids} onChange={onChange} />}
    <EditorialSEOFields values={entity} pending={disabled} errors={errors} />
  </>;
}
