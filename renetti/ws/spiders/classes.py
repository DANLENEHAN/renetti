import asyncio
import json
import os
from typing import Dict, List, Optional

import aiohttp

from renetti.ws.spiders.types import ListingUrlParsersMapper, ScrapedEquipment


class Spider:
    name: str
    base_file_path: str = "files"
    request_batch_limit: Optional[int]
    listing_group_parser_map: Dict[str, ListingUrlParsersMapper]

    listing_group_content_urls: Dict[str, List[str]]
    scraped_content_urls: List[str]
    scraped_data: List[ScrapedEquipment]

    def __init__(
        self,
        name: str,
        listing_group_parser_map: Dict[str, ListingUrlParsersMapper],
        overwrite_base_file_path: Optional[str] = None,
        request_batch_limit: Optional[int] = 100,
    ):
        self.name = name
        self.base_file_path = overwrite_base_file_path or self.base_file_path
        self.request_batch_limit = request_batch_limit
        self.listing_group_parser_map = listing_group_parser_map
        self._setup_spider()
        return

    def _setup_spider(self):
        self.file_path = f"{self.base_file_path}/{self.name}"
        os.makedirs(self.file_path, exist_ok=True)

        try:
            with open(f"{self.file_path}/listing_group_content_urls.json", "r") as f:
                self.listing_group_content_urls = json.load(f) or {}
        except FileNotFoundError:
            self.listing_group_content_urls = {}

        try:
            with open(f"{self.file_path}/scraped_content_urls.json", "r") as f:
                self.scraped_content_urls = json.load(f) or []
        except FileNotFoundError:
            self.scraped_content_urls = []
        return

    async def _scrape_listing_urls(self) -> Dict[str, List[str]]:
        print(f"(Scraper):({self.name}) - gathering content links")
        listing_group_content_urls = {
            listing_url: asyncio.create_task(parsers["content_url_parser"](url=listing_url))
            for listing_url, parsers in self.listing_group_parser_map.items()
        }
        return {u: await task for u, task in listing_group_content_urls.items()}

    def _scrape_content_link(
        self, listing_url: str, content_url: str, session: aiohttp.ClientSession
    ) -> asyncio.Task:
        parser_functions = self.listing_group_parser_map.get(listing_url)
        if parser_functions is None:
            raise NotImplementedError(
                f"(Scraper):({(self.name)}) - "
                f"has not implemented parser for listing_url '{listing_url}'"
            )
        return asyncio.create_task(
            parser_functions["content_page_parser"](url=content_url, session=session)
        )

    async def _scrape_content_urls(self):
        print(f"(Scraper):({(self.name)}) - beginning content scraping")
        scraped_data = []
        async with aiohttp.ClientSession() as session:
            scrape_tasks = []
            for listing_url, listing_group_content_urls in self.listing_group_content_urls.items():
                requests_sent = 0
                for content_url in listing_group_content_urls:
                    if content_url not in self.scraped_content_urls:
                        scrape_tasks.append(
                            self._scrape_content_link(
                                listing_url=listing_url, content_url=content_url, session=session
                            )
                        )
                        requests_sent += 1
                        if requests_sent == self.request_batch_limit:
                            requests_sent = 0
                            results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
                            for result in results:
                                if not isinstance(result, Exception):
                                    scraped_data.append(result)
                                    self.scraped_content_urls.append(content_url)
                            scrape_tasks = []
            if scrape_tasks:
                scraped_data += await asyncio.gather(*scrape_tasks)

            with open(f"{self.file_path}/scraped_content_urls.json", "w") as f:
                json.dump(self.scraped_content_urls, f, indent=3)
            self.scraped_content_urls = []
        return scraped_data

    async def _retrieve_content_urls(self):
        if not self.listing_group_content_urls:
            self.listing_group_content_urls = await self._scrape_listing_urls()
            with open(f"{self.file_path}/listing_group_content_urls.json", "w") as f:
                json.dump(self.listing_group_content_urls, f, indent=3)
        return self.listing_group_content_urls

    def _save_scraped_data(self):
        if self.scraped_data:
            with open(f"{self.file_path}/scraped_data.json", "w") as f:
                print(f"(Scraper):({(self.name)}) - saving scraped data")
                json.dump(self.scraped_data, f, indent=3)
                exit(0)
        else:
            print(f"(Scraper):({(self.name)}) - has no data to save exiting")
            exit(1)

    async def crawl_website(self):
        self.listing_group_content_urls = await self._retrieve_content_urls()
        self.scraped_data = await self._scrape_content_urls()
        self._save_scraped_data()
