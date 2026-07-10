"""Strip HTML to plain text.

Greenhouse returns posting bodies as HTML (sometimes entity-escaped). We unescape
once so any escaped markup becomes real tags, then walk the tags collecting the text
nodes. stdlib only — BeautifulSoup isn't worth a dependency for this. Step 3 feeds the
result to the shared matcher; step 4 stores it as the posting's jd_text.
"""

import html
from html.parser import HTMLParser


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        return " ".join(part.strip() for part in self._parts if part.strip())


def strip_html(content: str) -> str:
    """Return the visible text of an HTML fragment, whitespace-collapsed."""
    collector = _TextCollector()
    collector.feed(html.unescape(content))
    collector.close()
    return collector.text()
