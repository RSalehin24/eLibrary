import { CatalogEntityPage } from "@/components/catalog-entity-page";
import { entityMetadata, type EntityPageProps } from "@/lib/catalog-entity";

export const generateMetadata = (props: EntityPageProps) => entityMetadata("series", props);
export default function SeriesPage(props: EntityPageProps) {
  return <CatalogEntityPage kind="series" {...props} />;
}
