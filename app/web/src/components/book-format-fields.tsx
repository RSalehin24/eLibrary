
import { AdminText } from "@/components/admin-language";
import type { ManagedBookDetail } from "@/api/types";
import { EditorialField } from "./editorial-field";

export type BookFormatValues = Pick<ManagedBookDetail, "edition" | "language" | "publisher" | "is_compilation">;
type Props = { book: BookFormatValues; pending: boolean; errors: Record<string, string[]> };

export function BookFormatFields({ book, pending, errors }: Props) {
  return <fieldset disabled={pending}><legend><AdminText>{"সংস্করণ ও প্রকাশনার তথ্য"}</AdminText></legend>
    <EditorialField name="edition" label="সংস্করণ" value={book.edition} errors={errors.edition} maxLength={120} />
    <EditorialField name="language" label="বইয়ের ভাষার কোড (যেমন bn বা en)" value={book.language} errors={errors.language} maxLength={16} />
    <EditorialField name="publisher" label="প্রকাশক" value={book.publisher} errors={errors.publisher} maxLength={255} />
    <label className="checkbox-field"><input type="checkbox" name="is_compilation" defaultChecked={book.is_compilation} /><AdminText>{"সংকলন বই"}</AdminText></label>
  </fieldset>;
}
