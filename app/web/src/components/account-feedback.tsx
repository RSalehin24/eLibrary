"use client";

import { useEffect } from "react";
import { APIError } from "@/api/http";
import { AdminText } from "./admin-language";
import { useNotifications } from "./notification-provider";

export function AccountFeedback({ error, conflictMessage = "তথ্যটি অন্য জায়গায় বদলেছে। আপনার লেখা রেখে নতুন তথ্য মিলিয়ে নিন।" }: { error: Error | null; conflictMessage?: string }) {
  const { sound } = useNotifications();
  useEffect(() => { if (error) sound("error"); }, [error, sound]);
  if (!error) return null;
  const message = error instanceof APIError && error.code === "state_conflict" ? conflictMessage : error instanceof APIError && error.status === 400 ? "চিহ্নিত ঘরগুলোর তথ্য ঠিক করুন।" : "ফলাফল নিশ্চিত করা যায়নি। আবার পাঠানোর আগে বর্তমান অবস্থা দেখুন।";
  return <p className="field-error" role="alert"><AdminText>{message}</AdminText></p>;
}
