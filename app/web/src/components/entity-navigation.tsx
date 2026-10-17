import Link from "next/link";
import { AdminNavigation, AdminText } from "./admin-language";
import { Icon, type IconName } from "./icon";
import { entityLabels, type EntityKind } from "@/lib/catalog-entity";

const icons: Record<EntityKind, IconName> = { contributors: "people", categories: "tags", series: "books", collections: "read" };

export function EntityNavigation({ current }: { current: EntityKind }) {
  return <AdminNavigation className="entity-navigation" label="লেখক ও বিভাগের তালিকা">
    {(Object.keys(entityLabels) as EntityKind[]).map(kind => <Link key={kind} href={`/manage/entities/${kind}/`} aria-current={kind === current ? "page" : undefined}>
      <Icon name={icons[kind]} /><AdminText>{entityLabels[kind]}</AdminText>
    </Link>)}
  </AdminNavigation>;
}
