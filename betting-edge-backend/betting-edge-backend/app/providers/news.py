from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx
import xml.etree.ElementTree as ET


class NewsProviderError(RuntimeError):
    pass


class NewsProvider:
    """
    Retrieves current Google News RSS search results.

    This is a research feed, not an assertion that every headline
    is accurate. The application should display the source and
    publication time so the user can inspect the underlying report.
    """

    BASE_URL = "https://news.google.com/rss/search"

    async def search(self, query: str, limit: int = 10):
        if not query.strip():
            return []

        url = (
            f"{self.BASE_URL}"
            f"?q={quote(query)}"
            f"&hl=en-US"
            f"&gl=US"
            f"&ceid=US:en"
        )

        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers={
                    "User-Agent": (
                        "BettingEdgeResearch/1.0"
                    )
                },
            ) as client:
                response = await client.get(url)

            if response.status_code >= 400:
                raise NewsProviderError(
                    f"News provider returned HTTP "
                    f"{response.status_code}"
                )

            return self._parse(response.text, limit)

        except httpx.HTTPError as exc:
            raise NewsProviderError(
                f"News request failed: {exc}"
            ) from exc

    def _parse(self, xml_text: str, limit: int):
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise NewsProviderError(
                "Unable to parse news feed."
            ) from exc

        results = []

        for item in root.findall(".//item")[:limit]:
            title = self._text(item.find("title"))
            link = self._text(item.find("link"))
            description = self._text(
                item.find("description")
            )
            pub_date = self._text(
                item.find("pubDate")
            )

            published_at = None

            if pub_date:
                try:
                    published_at = (
                        parsedate_to_datetime(
                            pub_date
                        ).isoformat()
                    )
                except (TypeError, ValueError):
                    published_at = pub_date

            results.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "published_at": published_at,
                }
            )

        return results

    @staticmethod
    def _text(element):
        if element is None:
            return ""

        return "".join(
            element.itertext()
        ).strip()
