"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import Link from "next/link";
import { readSession } from "@/api/catalog";
import { readBookListControls } from "@/api/library";
import type { BookListControl } from "@/api/types";
import { Icon } from "./icon";
import { SaveBookButton } from "./save-book-button";
import { SiteText, useSiteLanguage } from "./site-language";

export function useBookListControls(slugs: readonly string[]) {
  const client = useQueryClient();
  const account = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const user = account.data?.user?.id;
  const available = account.data?.authenticated === true && !account.data.user?.totp_setup_required;
  const controls = useQuery({ queryKey: ["private", "book-list-controls", user, slugs], queryFn: ({ signal }) => readBookListControls(slugs, signal), enabled: available && slugs.length > 0, refetchOnWindowFocus: "always" });
  useEffect(() => { if (user) for (const entry of controls.data?.entries ?? []) client.setQueryData(["private", "saved-book", entry.slug, user], { saved: entry.saved }); }, [client, controls.data, user]);
  return { available, entries: new Map((controls.data?.entries ?? []).map(entry => [entry.slug, entry])), failed: available && controls.isError, retry: controls.refetch };
}

export function BookListActions({ control, onSaved }: { control?: BookListControl; onSaved?: () => void }) {
  const { t } = useSiteLanguage();
  if (!control) return null;
  return <div className="book-list-actions"><SaveBookButton slug={control.slug} initialSaved={control.saved} onSaved={onSaved} />
    {control.can_send_kindle && <Link className="button button-quiet" aria-label={t("কিন্ডলে পাঠান")} title={t("কিন্ডলে পাঠান")} href={`/kindle/books/${encodeURIComponent(control.slug)}/`}><Icon name="send" /><SiteText>কিন্ডলে পাঠান</SiteText></Link>}
  </div>;
}
