from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class RogueFitnessSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            url: ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
            for url in [
                "https://www.roguefitness.com/gb/weightlifting-bars-plates/barbells",
                "https://www.roguefitness.com/gb/weightlifting-bars-plates/bumpers",
                "https://www.roguefitness.com/gb/crossfit-equipment",
                "https://www.roguefitness.com/gb/rogue-rigs-racks",
            ]
        }

        super().__init__(
            name="roguefitness",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.AIOHTTP,
        )
        self.base_url = "https://www.roguefitness.com"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                urls = []
                page_number = 1
                while True:
                    await page.goto(url=f"{url}?page_number={page_number}")
                    html = await page.content()
                    soup = BeautifulSoup(markup=html, features="html.parser")
                    a_tags = soup.findAll("a", class_="hover-card")
                    urls += [f"{self.base_url}{a.get('href')}" for a in a_tags]
                    page_number += 1
                    try:
                        await page.wait_for_selector(
                            'a[aria-label="Category Pagination Next"]', timeout=2000
                        )
                    except Exception:
                        break
        return urls

    async def content_page_parser(
        self,
        url: str,
        session: aiohttp.ClientSession,
        *args,
        **kwargs,
    ) -> ScrapedEquipment:
        async with session.get(url=url) as response:
            html = await response.text()
            soup = BeautifulSoup(markup=html)
        return parse_product_json_ld_from_page(soup=soup)
