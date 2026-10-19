"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { readerSession } from "@/api/reading";
import type { ReaderAccess } from "@/api/types";
import { bookReadingLocation } from "@/lib/book-reading-location";
import { Icon } from "./icon";
import { SiteNumber, SiteText } from "./site-language";

export function BookLastLocation({ access }: { access: ReaderAccess }) {
  const identifier = access.active_session_id;
  const saved = !!access.reading_progress?.last_location;
  const matchingEdition = !!identifier && access.progress_session_id === identifier;
  const session = useQuery({ queryKey: ["private", "reading-location", matchingEdition ? identifier : null], queryFn: ({ signal }) => readerSession(identifier!, signal), enabled: matchingEdition && saved, retry: false, refetchOnWindowFocus: "always" });
  if (!saved) return null;
  const location = matchingEdition && session.data && !session.isError ? bookReadingLocation(session.data.reading_progress, session.data.chapters) : null;
  return <div className="book-last-location">
    <h3><SiteText>যেখানে পড়া থামিয়েছেন</SiteText></h3>
    {location ? <><p>{location.label}</p><p className="muted"><SiteText>অধ্যায়</SiteText> <SiteNumber value={location.number} /> / <SiteNumber value={location.total} />{location.percent !== null && <> · <SiteText>এই অধ্যায়ের</SiteText> <SiteNumber value={location.percent} />% <SiteText>পড়া হয়েছে</SiteText></>}</p></>
      : <p className="muted"><SiteText>{matchingEdition && session.isPending ? "শেষ পড়ার অবস্থান পাওয়া হচ্ছে…" : "পড়ার অবস্থান সংরক্ষিত আছে। বই খুললে সেটি ফিরিয়ে আনার চেষ্টা করা হবে।"}</SiteText></p>}
    {session.isError && <p className="notice" role="alert"><SiteText>শেষ অধ্যায়ের তথ্য পাওয়া যায়নি।</SiteText> <button className="button button-quiet" onClick={() => void session.refetch()}><SiteText>আবার দেখুন</SiteText></button></p>}
    {location && matchingEdition && session.data && !session.isError && <Link className="button" href={`/reader/${identifier}/`}><Icon name="read" /><SiteText>{location.percent === null ? "পড়া চালিয়ে যান" : "যেখানে থেমেছিলেন সেখান থেকে পড়ুন"}</SiteText></Link>}
  </div>;
}
