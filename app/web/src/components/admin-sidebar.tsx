"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useAdminLanguage } from "./admin-language";
import { Icon } from "./icon";

export function AdminSidebar({ children }: { children: React.ReactNode }) {
  const { t } = useAdminLanguage(), drawer = useRef<HTMLDialogElement>(null), trigger = useRef<HTMLButtonElement>(null), pathname = usePathname();
  useEffect(() => { drawer.current?.close(); }, [pathname]);
  return <aside className="admin-sidebar" aria-label={t("অ্যাডমিন মেনু")}>
    <div className="admin-desktop-navigation">{children}</div>
    <button ref={trigger} className="button button-quiet admin-menu-trigger" onClick={() => drawer.current?.showModal()}><Icon name="menu" />{t("মেনু খুলুন")}</button>
    <dialog ref={drawer} className="admin-navigation-drawer" aria-label={t("অ্যাডমিন মেনু")} onClose={() => trigger.current?.focus()}><div className="drawer-heading"><strong>{t("মূল কাজ")}</strong><button className="button button-quiet" onClick={() => drawer.current?.close()} aria-label={t("মেনু বন্ধ করুন")}><Icon name="close" /></button></div>{children}</dialog>
  </aside>;
}
