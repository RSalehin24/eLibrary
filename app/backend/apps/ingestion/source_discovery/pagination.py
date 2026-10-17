from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def next_archive_page(url):
    parsed = urlsplit(url)
    parameters = parse_qsl(parsed.query, keep_blank_values=True)
    current = [value for key, value in parameters if key == "_paged"]
    if current and (
        len(current) != 1 or not current[0].isdecimal() or int(current[0]) < 1
    ):
        raise ExecutionFailure(
            FailureKind.PERMANENT, "source_catalog_pagination_invalid"
        )
    page = int(current[0]) if current else 1
    parameters = [(key, value) for key, value in parameters if key != "_paged"]
    return urlunsplit(
        parsed._replace(query=urlencode([*parameters, ("_paged", page + 1)]))
    )
