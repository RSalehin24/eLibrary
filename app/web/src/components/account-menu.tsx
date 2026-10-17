"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { signOut } from "@/api/auth";
import { useAdminLanguage } from "./admin-language";
import type { WorkspaceSession } from "@/api/types";
import { Icon } from "./icon";

export function AccountMenu({ initial }: { initial?: WorkspaceSession }) {
  const { t } = useAdminLanguage();
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal), initialData: initial });
  const logout = useMutation({ mutationFn: signOut, onSuccess: () => {
    client.clear(); window.location.replace("/");
  } });
  if (!session.data?.authenticated) return <Link className="button button-quiet" href="/login/">{t("প্রবেশ করুন")}</Link>;
  return <div className="account-menu"><Link className="text-link" href="/profile/"><Icon name="people" />{t("প্রোফাইল")}</Link>{session.data.workspaces.manage && <Link className="text-link management-link" href="/manage/"><Icon name="overview" />{t("অ্যাডমিন")}</Link>}
    <button className="button button-quiet" onClick={() => logout.mutate()} disabled={logout.isPending}><Icon name="logout" />{t("প্রস্থান")}</button>
    {logout.error && <span className="field-error" role="alert">{t("প্রস্থান করা যায়নি। আবার চেষ্টা করুন।")}</span>}
  </div>;
}
