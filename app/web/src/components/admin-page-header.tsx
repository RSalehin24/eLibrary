import type { ReactNode } from "react";
import { Icon, type IconName } from "./icon";
import { AdminText } from "./admin-language";

export function AdminPageHeader({ title, description, icon, children }: { title: string; description: string; icon: IconName; children?: ReactNode }) {
  return <header className="admin-page-header"><div className="admin-page-intro"><span className="admin-page-icon"><Icon name={icon} size={24} /></span>
    <div><h1><AdminText>{title}</AdminText></h1><p className="admin-page-description"><AdminText>{description}</AdminText></p></div></div>
    {children && <div className="admin-page-actions">{children}</div>}
  </header>;
}
