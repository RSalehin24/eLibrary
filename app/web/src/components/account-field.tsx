"use client";

import { useAdminLanguage } from "./admin-language";

type AccountFieldProps = { name: string; label: string; initial?: string; errors?: string[]; type?: "text" | "email" | "password"; autoComplete?: string; minLength?: number; maxLength?: number; required?: boolean; multiline?: boolean; disabled?: boolean };

export function AccountField({ name, label, initial, errors, multiline, ...options }: AccountFieldProps) {
  const { t } = useAdminLanguage();
  const attributes = { id: name, name, defaultValue: initial, ...options, "aria-invalid": Boolean(errors?.length), "aria-describedby": errors?.length ? `${name}-error` : undefined };
  return <div className="form-field"><label htmlFor={name}>{t(label)}</label>
    {multiline ? <textarea {...attributes} rows={4} /> : <input {...attributes} />}
    {errors?.length ? <p className="field-error" id={`${name}-error`}>{errors.join(" ")}</p> : null}
  </div>;
}
