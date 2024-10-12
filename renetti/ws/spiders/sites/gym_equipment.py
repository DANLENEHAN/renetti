from typing import List

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class GymEquipmentSpider(Spider):
    def __init__(self):
        listing_group_parser_map = {
            "https://gymequipment.co.uk/strength-conditioning?product_list_limit=all": {
                "content_url_parser": self.content_url_parser_all,
                "content_page_parser": self.content_page_parser_all,
            }
        }
        super().__init__(
            name="gymequipment",
            listing_group_parser_map=listing_group_parser_map,
            content_request_method=RequestMethod.AIOHTTP,
        )

    async def content_url_parser_all(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url)
                await page.wait_for_selector(".product-item-photo")
                html_source = await page.content()
                soup = BeautifulSoup(html_source, "html.parser")
                a_elements = soup.find_all("a", class_="product-item-photo")
        return [a.get("href") for a in a_elements]

    async def content_page_parser_all(
        self,
        url: str,
        session: aiohttp.ClientSession,
        *args,
        **kwargs,
    ) -> ScrapedEquipment:
        async with session.get(url) as response:
            raw_html = await response.text()
            soup = BeautifulSoup(raw_html, "html.parser")
            equipment_image = soup.find(
                "div",
                class_=[
                    "fotorama__stage__frame",
                    "fotorama__active",
                    "fotorama_vertical_ratio",
                    "fotorama__loaded",
                    "fotorama__loaded--img",
                ],
            )
            equipment_image_link = (
                equipment_image.find("img").get("src") if equipment_image else None
            )
        scraped_equipment = parse_product_json_ld_from_page(soup=soup)
        scraped_equipment["image_links"] = [equipment_image_link]
        return scraped_equipment
