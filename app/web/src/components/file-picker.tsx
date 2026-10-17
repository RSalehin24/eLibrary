"use client";

import { useEffect, useRef, useState, type ComponentProps } from "react";
import { useSiteLanguage } from "./site-language";

export function FilePicker(props: ComponentProps<"input">) {
  const { t } = useSiteLanguage();
  const input = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  useEffect(() => {
    const form = input.current?.form;
    const reset = () => setName("");
    form?.addEventListener("reset", reset);
    return () => form?.removeEventListener("reset", reset);
  }, []);
  return <div className="file-picker"><div className="file-picker-control"><span className="button button-quiet" aria-hidden="true">{t("ফাইল বেছে নিন")}</span>
    <input {...props} ref={input} type="file" className="file-picker-native" onChange={(event) => { setName(Array.from(event.target.files ?? []).map((file) => file.name).join(", ")); props.onChange?.(event); }} />
  </div><span className="file-picker-name" role="status">{name || t("কোনো ফাইল বাছা হয়নি")}</span></div>;
}
