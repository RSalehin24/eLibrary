"use client";

import Image from "next/image";
import { useState } from "react";
import { BrandMark } from "./brand-mark";
import { SiteText } from "./site-language";

export function BookCover({ title, author, coverUrl }: { title: string; author?: string; coverUrl?: string | null }) {
  const [failed, setFailed] = useState<string | null>(null);
  if (coverUrl && failed !== coverUrl) return <div className="book-cover book-cover-media" aria-hidden="true"><Image className="book-cover-image" src={coverUrl} alt="" width={208} height={300} unoptimized onError={() => setFailed(coverUrl)} /></div>;
  return <div className="book-cover" aria-hidden="true"><div className="book-cover-art">
    <div className="cover-imprint"><BrandMark size={24} /><SiteText>বাংলা পাঠাগার</SiteText></div>
    <span className="cover-title">{title}</span>{author && <small className="cover-author">{author}</small>}
    <div className="cover-rule" />
  </div></div>;
}

