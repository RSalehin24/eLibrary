def catalog_result_anchors(soup):
    anchors = []
    for result in soup.select(".facetwp-template .fwpl-result"):
        anchor = result.select_one(".fwpl-item.el-97dha a[href]") or next(
            (
                link
                for link in result.select("a[href]")
                if link.get_text(" ", strip=True)
            ),
            None,
        )
        if anchor is not None:
            anchors.append(anchor)
    return anchors
