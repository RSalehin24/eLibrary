import type { BackgroundJob } from "@/api/types";
import { AdminNumber, AdminText } from "./admin-language";
import { Icon } from "./icon";

const nestedLayouts = new Set(["lesson_topic_nested", "mixed_lessons_and_topics", "sectioned_flat_lessons", "sectioned_lesson_topic_nested", "sectioned_mixed_lessons_and_topics"]);

export function SourceLayoutSummary({ layout }: { layout: BackgroundJob["source_layout"] }) {
  if (!layout) return null;
  const nested = nestedLayouts.has(layout.structure_type);
  if (!layout.multi_page && !nested) return null;
  return <div className={layout.contents_incomplete ? "notice" : "source-layout-summary"}>
    <p><Icon name="books" /><AdminText>{layout.multi_page ? "একাধিক পাতায় সূচিপত্র" : "একাধিক স্তরের সূচিপত্র"}</AdminText>{layout.multi_page && nested && <> · <AdminText>একাধিক স্তরের সূচিপত্র</AdminText></>}</p>
    {layout.contents_pages > 0 && <p><AdminText>সংগৃহীত সূচিপত্রের পাতা</AdminText>: <AdminNumber value={layout.collected_contents_pages} /> / <AdminNumber value={layout.contents_pages} /></p>}
    {layout.contents_incomplete && <p><AdminText>সূচিপত্রের সব পাতা পাওয়া যায়নি। সম্পূর্ণ লেখা সংগ্রহের আগে বই প্রকাশিত হবে না।</AdminText></p>}
  </div>;
}
