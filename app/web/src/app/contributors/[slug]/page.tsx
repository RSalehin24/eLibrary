import { CatalogEntityPage } from "@/components/catalog-entity-page";
import { entityMetadata, type EntityPageProps } from "@/lib/catalog-entity";

export const generateMetadata = (props: EntityPageProps) => entityMetadata("contributors", props);
export default function ContributorPage(props: EntityPageProps) {
  return <CatalogEntityPage kind="contributors" {...props} />;
}
