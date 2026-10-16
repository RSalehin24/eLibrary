import { CatalogEntityPage } from "@/components/catalog-entity-page";
import { entityMetadata, type EntityPageProps } from "@/lib/catalog-entity";

export const generateMetadata = (props: EntityPageProps) => entityMetadata("categories", props);
export default function CategoryPage(props: EntityPageProps) {
  return <CatalogEntityPage kind="categories" {...props} />;
}
