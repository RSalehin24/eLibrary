import { CatalogEntityPage } from "@/components/catalog-entity-page";
import { entityMetadata, type EntityPageProps } from "@/lib/catalog-entity";

export const generateMetadata = (props: EntityPageProps) => entityMetadata("collections", props);
export default function CollectionPage(props: EntityPageProps) {
  return <CatalogEntityPage kind="collections" {...props} />;
}
