import sys
from types import ModuleType
from unittest.mock import Mock

from apps.ingestion.pipeline.epub_properties.epub_builder import _generate_cover_png


def test_unavailable_text_shaping_uses_html_cover_without_attempting_png(
    monkeypatch, tmp_path
):
    pillow = ModuleType("PIL")
    pillow.Image = Mock()
    pillow.ImageDraw = Mock()
    pillow.features = Mock()
    pillow.features.check_feature.return_value = False
    monkeypatch.setitem(sys.modules, "PIL", pillow)
    result = _generate_cover_png(
        book_title="বাংলা বই", author="বাংলা লেখক", series="", output_folder=str(tmp_path)
    )
    assert result is None
    pillow.features.check_feature.assert_called_once_with("raqm")
    pillow.Image.new.assert_not_called()
