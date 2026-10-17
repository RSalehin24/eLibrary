import { SiteFieldErrors } from "./site-field-errors";

import { AdminText } from "@/components/admin-language";
import type { ManagedBookDetail } from "@/api/types";
import { EditorialField } from "./editorial-field";

export type BookFormatValues = Pick<ManagedBookDetail, "edition" | "manual_language" | "manual_publisher" | "manual_price" | "manual_binding" | "manual_is_compilation">;
type Props = { book: BookFormatValues; pending: boolean; errors: Record<string, string[]> };

export function BookFormatFields({ book, pending, errors }: Props) {
  return <fieldset disabled={pending}><legend><AdminText>{"সংস্করণ ও প্রকাশনার তথ্য"}</AdminText></legend>
    <EditorialField name="edition" label="সংস্করণ" value={book.edition} errors={errors.edition} maxLength={120} />
    <EditorialField name="manual_language" label="বইয়ের ভাষার কোড (যেমন bn বা en)" value={book.manual_language} errors={errors.manual_language} maxLength={16} />
    <EditorialField name="manual_publisher" label="প্রকাশক" value={book.manual_publisher} errors={errors.manual_publisher} maxLength={255} />
    <div className="form-field"><label htmlFor="manual_price"><AdminText>{"মূল্য (ঐচ্ছিক)"}</AdminText></label>
      <input id="manual_price" name="manual_price" type="number" min="0" max="99999999.99" step="0.01" defaultValue={book.manual_price ?? ""} aria-invalid={!!errors.manual_price?.length} aria-describedby={errors.manual_price?.length ? "manual_price-error" : undefined} />
      {errors.manual_price?.length ? <p className="field-error" id="manual_price-error"><SiteFieldErrors errors={errors.manual_price} /></p> : null}</div>
    <div className="form-field"><label htmlFor="manual_binding"><AdminText>{"বাঁধাই"}</AdminText></label><select id="manual_binding" name="manual_binding" defaultValue={book.manual_binding} aria-invalid={!!errors.manual_binding?.length} aria-describedby={errors.manual_binding?.length ? "manual_binding-error" : undefined}>
      <option value=""><AdminText>{"উল্লেখ নেই"}</AdminText></option><option value="paper_back"><AdminText>{"পেপারব্যাক"}</AdminText></option><option value="hard_cover"><AdminText>{"হার্ডকভার"}</AdminText></option></select>
      {errors.manual_binding?.length ? <p className="field-error" id="manual_binding-error"><SiteFieldErrors errors={errors.manual_binding} /></p> : null}</div>
    <label className="checkbox-field"><input type="checkbox" name="manual_is_compilation" defaultChecked={book.manual_is_compilation} /><AdminText>{"সংকলন বই"}</AdminText></label>
  </fieldset>;
}
