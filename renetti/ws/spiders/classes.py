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
        request_batch_limit: Optional[int] = 100,
    ):
        self.name = name
        self.listing_url_parser_mapper = listing_url_parser_mapper
        self.listing_url_content_links = {}
        self.listing_url_content_data = []
        self.file_path = overwrite_file_path or self.file_path
        self.request_batch_limit = request_batch_limit
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
        scraped_data = []
        async with aiohttp.ClientSession() as session:
            scrape_tasks = []
            for listing_url, content_urls in self.listing_url_content_links.items():
                requests_sent = 0
                for content_url in content_urls:
                    print(requests_sent, content_url)
                    scrape_tasks.append(
                        self._scrape_content_link(
                            listing_url=listing_url, content_url=content_url, session=session
                        )
                    )
                    requests_sent += 1
                    if requests_sent == self.request_batch_limit:
                        requests_sent = 0
                        scraped_data += await asyncio.gather(*scrape_tasks)
                        scrape_tasks = []
            if scrape_tasks:
                scraped_data += await asyncio.gather(*scrape_tasks)
        return scraped_data

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
