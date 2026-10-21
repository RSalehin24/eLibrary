"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { signOut } from "@/api/auth";
import type { WorkspaceSession } from "@/api/types";
import { Icon, type IconName } from "./icon";
import { SiteLanguageSwitch, useSiteLanguage } from "./site-language";

const links: { href: string; label: string; icon: IconName }[] = [
  { href: "/profile/", label: "প্রোফাইল", icon: "people" },
  { href: "/physical-books/", label: "কাগজের বই", icon: "books" },
  { href: "/local-reader/", label: "নিজের EPUB পড়ুন", icon: "read" },
  { href: "/help/", label: "সহায়তা", icon: "help" },
];

export function AccountMenu({ initial }: { initial?: WorkspaceSession }) {
  const { t } = useSiteLanguage(), menu = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal), initialData: initial });
  const logout = useMutation({ mutationFn: signOut, onSuccess: () => { client.clear(); window.location.replace("/"); } });
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => { if (event.target instanceof Node && !menu.current?.contains(event.target)) menu.current?.removeAttribute("open"); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape" && menu.current?.open) { menu.current.open = false; menu.current.querySelector("summary")?.focus(); } };
    document.addEventListener("pointerdown", closeOutside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", closeOutside); document.removeEventListener("keydown", escape); };
  }, []);
  if (!session.data?.authenticated) return <div className="guest-account"><Link className="button button-quiet" href="/login/">{t("প্রবেশ করুন")}</Link><details className="account-menu guest-preferences" ref={menu}><summary className="button button-quiet" aria-label="Language / ভাষা"><Icon name="settings" /></summary><div className="account-menu-panel"><SiteLanguageSwitch /></div></details></div>;
  return <details className="account-menu" ref={menu}><summary className="button button-quiet" aria-label={t("অ্যাকাউন্ট মেনু")}><Icon name="people" /><span className="account-action-label">{t("অ্যাকাউন্ট")}</span><Icon name="chevron" size={14} /></summary>
    <div className="account-menu-panel"><SiteLanguageSwitch />
      <>{links.map(link => <Link key={link.href} href={link.href} aria-current={pathname.startsWith(link.href) ? "page" : undefined} onClick={() => { if (menu.current) menu.current.open = false; }}><Icon name={link.icon} />{t(link.label)}</Link>)}
        <button type="button" onClick={() => logout.mutate()} disabled={logout.isPending}><Icon name="logout" />{t("প্রস্থান")}</button></>
      {logout.error && <p className="field-error" role="alert">{t("প্রস্থান করা যায়নি। আবার চেষ্টা করুন।")}</p>}
    </div>
  </details>;
}
