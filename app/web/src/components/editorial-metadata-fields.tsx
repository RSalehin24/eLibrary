
import { AdminText } from "@/components/admin-language";
import type { EditorialValues } from "@/lib/editorial-fields";
import { EditorialField } from "./editorial-field";

type FieldProps = { values: EditorialValues; errors: Record<string, string[]>; pending: boolean };

export function EditorialTextFields({ values, errors }: Omit<FieldProps, "pending">) {
  return <>
    <EditorialField name="editorial_description" label="সম্পাদকীয় বর্ণনা" value={values.editorial_description} errors={errors.editorial_description} multiline maxLength={20000} />
    <EditorialField name="alternative_names" label="যাচাইকৃত বিকল্প নাম (প্রতি লাইনে একটি, সর্বোচ্চ ২০টি)" value={values.alternative_names.join("\n")} errors={errors.alternative_names} multiline maxLength={5120} />
  </>;
}

export function EditorialSEOFields({ values, errors, pending }: FieldProps) {
  return <fieldset disabled={pending}>
    <legend><AdminText>{"সার্চ ইঞ্জিন ও সামাজিক মাধ্যমে পরিচিতি"}</AdminText></legend>
    <EditorialField name="seo_title" label="সার্চের শিরোনাম (ঐচ্ছিক)" value={values.seo_title} errors={errors.seo_title} maxLength={160} />
    <EditorialField name="seo_description" label="সার্চের বর্ণনা (ঐচ্ছিক)" value={values.seo_description} errors={errors.seo_description} multiline maxLength={320} />
    <EditorialField name="social_image_url" label="সামাজিক মাধ্যমের ছবির HTTPS ঠিকানা (ঐচ্ছিক)" value={values.social_image_url} errors={errors.social_image_url} maxLength={1000} />
    <label className="checkbox-field"><input type="checkbox" name="indexing_eligible" defaultChecked={values.indexing_eligible} /><AdminText>{"সার্চ ইঞ্জিনে দেখানোর অনুমতি"}</AdminText></label>
    <p className="muted"><AdminText>{"বিবরণ যোগ করা থাকলে প্রকাশিত তথ্য সার্চ ইঞ্জিনে দেখা যাবে।"}</AdminText></p>
  </fieldset>;
}
