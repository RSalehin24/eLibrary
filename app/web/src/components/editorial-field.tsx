"use client";

import { useAdminLanguage } from "./admin-language";

type EditorialFieldProps = { name: string; label: string; value: string; errors?: string[]; multiline?: boolean; maxLength: number };

export function EditorialField({ name, label, value, errors, multiline, maxLength }: EditorialFieldProps) {
  const { t } = useAdminLanguage();
  const attributes = { id: name, name, defaultValue: value, maxLength,
    "aria-invalid": Boolean(errors?.length), "aria-describedby": errors?.length ? `${name}-error` : undefined };
  return <div className="form-field"><label htmlFor={name}>{t(label)}</label>
    {multiline ? <textarea {...attributes} rows={5} /> : <input {...attributes} />}
    {errors?.length ? <p className="field-error" id={`${name}-error`}>{errors.join(" ")}</p> : null}
  </div>;
}
