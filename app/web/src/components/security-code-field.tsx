import { SiteFieldErrors } from "./site-field-errors";
import { SiteText } from "@/components/site-language";
export function SecurityCodeField({ errors }: { errors?: string[] }) {
  return <div className="form-field"><label htmlFor="security_token"><SiteText>{"অ্যাপের নিরাপত্তা কোড"}</SiteText></label>
    <input id="security_token" name="token" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}([0-9]{2})?" minLength={6} maxLength={8} required aria-invalid={Boolean(errors?.length)} aria-describedby={errors?.length ? "security_token-error" : undefined} />
    {errors?.length ? <p className="field-error" id="security_token-error"><SiteFieldErrors errors={errors} /></p> : null}
  </div>;
}
