import asyncio
import json
from typing import Dict, List, Optional

import aiohttp

from renetti.ws.spiders.types import ListingUrlParsersMapper, ScrapedEquipment


class Spider:
    name: str
    file_path: str = "files"
    listing_url_parser_mapper: Dict[str, ListingUrlParsersMapper]
    listing_url_content_links: Dict[str, List[str]]
    listing_url_content_data: List[ScrapedEquipment]

    def __init__(
        self,
        name: str,
        listing_url_parser_mapper: Dict[str, ListingUrlParsersMapper],
        overwrite_file_path: Optional[str] = None,
    ):
        self.name = name
        self.listing_url_parser_mapper = listing_url_parser_mapper
        self.listing_url_content_links = {}
        self.listing_url_content_data = []
        self.file_path = overwrite_file_path or self.file_path
        return

    async def _gather_content_links(self) -> Dict[str, List[str]]:
        print(f"(Scraper):({self.name}) - gathering content links")
        listing_url_content_links = {
            listing_url: asyncio.create_task(parsers["content_url_parser"](url=listing_url))
            for listing_url, parsers in self.listing_url_parser_mapper.items()
        }
        return {u: await task for u, task in listing_url_content_links.items()}

    def _scrape_content_link(
        self, listing_url: str, content_url: str, session: aiohttp.ClientSession
    ) -> asyncio.Task:
        print(
            f"(Scraper):({self.name}) - scraping content link "
            f"'{content_url}' from listing '{listing_url}'"
        )
        parser_functions = self.listing_url_parser_mapper.get(listing_url)
        if parser_functions is None:
            raise NotImplementedError(
                f"(Scraper):({(self.name)}) - "
                f"has not implemented parser for listing_url '{listing_url}'"
            )
        return asyncio.create_task(
            parser_functions["content_page_parser"](url=content_url, session=session)
        )

    async def _scrape_all_content_links(self):
        print(f"(Scraper):({(self.name)}) - beginning content scraping")
        scrape_tasks = []
        async with aiohttp.ClientSession() as session:
            for listing_url, content_urls in self.listing_url_content_links.items():
                for content_url in content_urls:
                    print(content_url)
                    scrape_tasks.append(
                        self._scrape_content_link(
                            listing_url=listing_url, content_url=content_url, session=session
                        )
                    )
            return await asyncio.gather(*scrape_tasks)

    def _save_crawled_data(self):
        if self.listing_url_content_data:
            with open(f"{self.file_path}/{self.name}_crawled_data.json", "w") as f:
                print(f"(Scraper):({(self.name)}) - saving scraped data")
                f.write(json.dumps(self.listing_url_content_data, indent=3))
                exit(0)
        else:
            print(f"(Scraper):({(self.name)}) - has no data to save exiting")
            exit(1)

    async def crawl_website(self):
        self.listing_url_content_links = await self._gather_content_links()
        self.listing_url_content_data = await self._scrape_all_content_links()
        self._save_crawled_data()
