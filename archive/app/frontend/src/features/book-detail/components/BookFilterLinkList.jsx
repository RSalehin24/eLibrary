import { Fragment } from "react";
import { Link } from "react-router-dom";
import { toQueryString } from "../../../utils/query";

export default function BookFilterLinkList({
  emptyLabel = "",
  extraFilters = {},
  queryKey,
  values,
}) {
  if (!values?.length) {
    return emptyLabel || null;
  }

  return values.map((value, index) => (
    <Fragment key={`${queryKey}-${value}`}>
      <Link
        to={`/library${toQueryString({ ...extraFilters, [queryKey]: value })}`}
        className="meta-link"
      >
        {value}
      </Link>
      {index < values.length - 1 ? (
        <span className="meta-divider">, </span>
      ) : null}
    </Fragment>
  ));
}
