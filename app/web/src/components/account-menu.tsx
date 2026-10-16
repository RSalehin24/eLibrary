"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import { signOut } from "@/api/auth";

export function AccountMenu() {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const logout = useMutation({ mutationFn: signOut, onSuccess: () => {
    client.clear(); window.location.replace("/");
  } });
  if (!session.data?.authenticated) return <Link className="button button-quiet" href="/login/">প্রবেশ করুন</Link>;
  return <div className="account-menu"><Link className="text-link" href="/profile/">প্রোফাইল</Link>{session.data.workspaces.manage && <Link className="text-link management-link" href="/manage/">পরিচালনা</Link>}
    <button className="button button-quiet" onClick={() => logout.mutate()} disabled={logout.isPending}>প্রস্থান</button>
    {logout.error && <span className="field-error" role="alert">প্রস্থান করা যায়নি। আবার চেষ্টা করুন।</span>}
  </div>;
}
