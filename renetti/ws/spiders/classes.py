import asyncio
import json
import os
from typing import Dict, List, Optional

import aiohttp
from playwright.async_api import Browser, async_playwright

from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment


class Spider:

    # Base Class Attributes
    base_file_path: str = "files"
    listing_group_content_urls: Dict[str, List[str]]
    scraped_content_urls: List[str]

    # Init Class Attributes
    name: str
    request_batch_limit: Optional[int]
    listing_group_parser_map: Dict[str, ListingUrlParsersMapper]
    content_request_method: RequestMethod

    def __init__(
        self,
        name: str,
        listing_group_parser_map: Dict[str, ListingUrlParsersMapper],
        content_request_method: RequestMethod,
        request_batch_limit: Optional[int] = 100,
    ):
        self.name = name
        self.request_batch_limit = request_batch_limit
        self.listing_group_parser_map = listing_group_parser_map
        self.content_request_method = content_request_method
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
        async with async_playwright() as playwright:
            async with await playwright.chromium.launch(headless=False) as browser:
                listing_group_content_urls = {
                    listing_url: asyncio.create_task(
                        parsers["content_url_parser"](url=listing_url, browser=browser)
                    )
                    for listing_url, parsers in self.listing_group_parser_map.items()
                }
                results = await asyncio.gather(*listing_group_content_urls.values())
        return {
            listing_url: result
            for listing_url, result in zip(listing_group_content_urls.keys(), results)
        }

    def _scrape_content_link(
        self,
        listing_url: str,
        content_url: str,
        session: aiohttp.ClientSession,
        browser: Browser,
    ) -> asyncio.Task:
        parser_functions = self.listing_group_parser_map.get(listing_url)
        if parser_functions is None:
            raise NotImplementedError(
                f"(Scraper):({(self.name)}) - "
                f"has not implemented parser for listing_url '{listing_url}'"
            )
        return asyncio.create_task(
            parser_functions["content_page_parser"](
                url=content_url,
                session=session,
                browser=browser,
            )
        )

    async def _retrive_and_save_successful_results(
        self, tasks: List[asyncio.Task], scraped_urls: List[str]
    ) -> None:
        scraped_data = []
        scraped_content_urls = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for index, result in enumerate(results):
            if not isinstance(result, BaseException):
                scraped_data.append(result)
                scraped_content_urls.append(scraped_urls[index])
            else:
                print(f"Url '{scraped_urls[index]}' - recieved exception '{str(result)}'")
        self._save_scraped_content_data(scraped_data=scraped_data)
        self._update_and_save_scraped_content_urls(scraped_content_urls=scraped_content_urls)
        return

    async def _scrape_content_urls(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        browser: Optional[Browser] = None,
    ):
        scrape_tasks = []
        scraped_urls = []
        for listing_url, group_content_urls in self.listing_group_content_urls.items():
            print(f"(Scraper):({self.name}) - beginning scraping of listing group '{listing_url}'")
            requests_sent = 0
            for content_url in group_content_urls:
                if content_url not in self.scraped_content_urls:
                    scrape_tasks.append(
                        self._scrape_content_link(
                            listing_url=listing_url,
                            content_url=content_url,
                            session=session,
                            browser=browser,
                        )
                    )
                    scraped_urls.append(content_url)
                    requests_sent += 1
                    if requests_sent == self.request_batch_limit:
                        await self._retrive_and_save_successful_results(
                            tasks=scrape_tasks,
                            scraped_urls=scraped_urls,
                        )
                        requests_sent = 0
                        scrape_tasks = []
                        scraped_urls = []
            print(f"(Scraper):({self.name}) - completed scraping of listing group '{listing_url}'")
        if scrape_tasks:
            await self._retrive_and_save_successful_results(
                tasks=scrape_tasks,
                scraped_urls=scraped_urls,
            )
        return

    async def _retrieve_content_url_data(self):
        print(f"(Scraper):({(self.name)}) - beginning content scraping")
        if self.content_request_method == RequestMethod.AIOHTTP:
            async with aiohttp.ClientSession() as session:
                scraped_data = await self._scrape_content_urls(session=session)
        elif self.content_request_method == RequestMethod.PLAYWRIGHT:
            async with async_playwright() as playwright:
                async with await playwright.chromium.launch(headless=False) as browser:
                    scraped_data = await self._scrape_content_urls(browser=browser)
        return scraped_data

    async def _retrieve_content_urls(self):
        if not self.listing_group_content_urls:
            self.listing_group_content_urls = await self._scrape_listing_urls()
            with open(f"{self.file_path}/listing_group_content_urls.json", "w") as f:
                json.dump(self.listing_group_content_urls, f, indent=3)
        return

    def _update_and_save_scraped_content_urls(self, scraped_content_urls: List[str]):
        if scraped_content_urls:
            if os.path.exists(f"{self.file_path}/scraped_content_urls.json"):
                with open(f"{self.file_path}/scraped_content_urls.json", "r") as f:
                    last_run_data = json.load(f)
            else:
                last_run_data = []
            self.scraped_content_urls = last_run_data + scraped_content_urls
            # Now open the file in write mode to save the combined data
            with open(f"{self.file_path}/scraped_content_urls.json", "w") as f:
                json.dump(self.scraped_content_urls, f, indent=3)
        return

    def _save_scraped_content_data(self, scraped_data: List[ScrapedEquipment]):
        if scraped_data:
            if os.path.exists(f"{self.file_path}/scraped_data.json"):
                with open(f"{self.file_path}/scraped_data.json", "r") as f:
                    last_run_data = json.load(f)
            else:
                last_run_data = []
            # Now open the file in write mode to save the combined data
            with open(f"{self.file_path}/scraped_data.json", "w") as f:
                json.dump(last_run_data + scraped_data, f, indent=3)
        return

    async def crawl_website(self):
        await self._retrieve_content_urls()
        await self._retrieve_content_url_data()
        print(f"(Scraper):({self.name}) - all scraping completed")
        exit(0)
