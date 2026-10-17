"use client";

import { useRef, type ReactNode, type RefObject } from "react";
import { useAdminLanguage } from "./admin-language";
import { Icon, type IconName } from "./icon";

export function AdminDialog({ title, trigger, children, dialogRef, disabled, icon, className = "button button-quiet" }: { title: string; trigger: string; children: ReactNode; dialogRef?: RefObject<HTMLDialogElement | null>; disabled?: boolean; icon?: IconName; className?: string }) {
  const local = useRef<HTMLDialogElement>(null);
  const dialog = dialogRef ?? local;
  const triggerButton = useRef<HTMLButtonElement>(null);
  const { t } = useAdminLanguage();
  return <><button ref={triggerButton} type="button" className={className} disabled={disabled} onClick={() => dialog.current?.showModal()}>{icon && <Icon name={icon} />}{t(trigger)}</button>
    <dialog className="admin-dialog" ref={dialog} aria-label={t(title)} onClose={() => triggerButton.current?.focus()}><div className="dialog-heading"><h2>{t(title)}</h2><button className="button button-quiet" type="button" onClick={() => dialog.current?.close()}>{t("বন্ধ করুন")}</button></div>{children}</dialog></>;
}
