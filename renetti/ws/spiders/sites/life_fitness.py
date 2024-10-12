from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class LifeFitnessSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            "https://www.lifefitness.com/en-us/catalog": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
        }

        super().__init__(
            name="lifefitness",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.AIOHTTP,
        )
        self.base_url = "https://www.lifefitness.com"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                page_number = 1
                urls = []
                while True:
                    await page.goto(url=f"{url}/?pageNumber={page_number}#searchform")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    html = await page.content()
                    soup = BeautifulSoup(markup=html, features="html.parser")
                    urls += [
                        f"{self.base_url}{u.get("href")}"
                        for u in soup.findAll("a", class_="product-grid--item")
                    ]
                    try:
                        await page.wait_for_selector('a[title="Next"]', timeout=2000)
                    except Exception:
                        break
                    page_number += 1
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
