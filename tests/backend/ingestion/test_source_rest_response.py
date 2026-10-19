from unittest.mock import Mock

import pytest
from apps.ingestion.pipeline.book_manifest import _fetch_via_wp_rest_api


@pytest.mark.parametrize('payload', [[], {'content': []}, {'content': 'invalid'}])
def test_invalid_rest_shapes_do_not_become_reading_text(payload):
    session = Mock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = payload
    assert _fetch_via_wp_rest_api(session, 123) is None


def test_rest_collection_does_not_hide_unexpected_application_errors():
    session = Mock()
    session.get.side_effect = RuntimeError('collector defect')
    with pytest.raises(RuntimeError, match='collector defect'):
        _fetch_via_wp_rest_api(session, 123)
