from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class HoistFitnessSpider(Spider):
    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            url: ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
            for url in [
                "https://www.hoistfitness.com/collections/cpl-club-line",
                "https://www.hoistfitness.com/collections/cpl-freeweights",
                "https://www.hoistfitness.com/collections/cpl-exercise-bikes",
                "https://www.hoistfitness.com/collections/cpl-hd-dual-series",
                "https://www.hoistfitness.com/collections/cpl-motioncage",
                "https://www.hoistfitness.com/collections/cpl-multi-jungle-systems",
                "https://www.hoistfitness.com/pages/performance-series",
                "https://www.hoistfitness.com/collections/cpl-roc-it-plate-loaded",
                "https://www.hoistfitness.com/collections/cpl-roc-it-selectorized",
                "https://www.hoistfitness.com/collections/ccat-benches-racks",
                "https://www.hoistfitness.com/collections/ccat-exercise-bikes",
                "https://www.hoistfitness.com/pages/performance-accessories",
                "https://www.hoistfitness.com/collections/ccat-hd-dual-series",
                "https://www.hoistfitness.com/collections/ccat-motioncage",
                "https://www.hoistfitness.com/collections/ccat-multi-jungle-systems",
                "https://www.hoistfitness.com/collections/ccat-weight-storage-racks",
                "https://www.hoistfitness.com/collections/ccat-selectorized",
                "https://www.hoistfitness.com/collections/ccat-plate-loaded",
            ]
        }

        super().__init__(
            name="hoistfitness",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.AIOHTTP,
        )
        self.base_url = "https://www.hoistfitness.com/"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url=url)
                await page.wait_for_timeout(2000)
                html = await page.content()
                soup = BeautifulSoup(markup=html, features="html.parser")
        return [
            f"{self.base_url}{a.get('href')}" for a in soup.findAll("a", class_="product_card_img")
        ]

    async def content_page_parser(
        self,
        url: str,
        session: aiohttp.ClientSession,
        *args,
        **kwargs,
    ) -> ScrapedEquipment:
        async with await session.get(url=url) as response:
            html = await response.text()
            soup = BeautifulSoup(markup=html, features="html.parser")
            scraped_equipment = parse_product_json_ld_from_page(soup=soup)
            categories = [url.split("collections/")[1].split("/")[0]]
            scraped_equipment["categories"] = categories
            scraped_equipment[
                "name"
            ] += f' {soup.find("div", class_="product_card_sku").find("h3").text.strip()}'
        return scraped_equipment
