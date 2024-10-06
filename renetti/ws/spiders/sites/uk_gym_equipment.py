import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import (
    EquipmentSpecification,
    ListingUrlParsersMapper,
    ScrapedEquipment,
)


class UkGymEquipmentSpider(Spider):
    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            "https://www.ukgymequipment.com/cardio-machines-c11": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser_all,
                content_page_parser=self.content_page_parser_all,
            ),
            "https://www.ukgymequipment.com/strength-training-c8": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser_all,
                content_page_parser=self.content_page_parser_all,
            ),
            "https://www.ukgymequipment.com/free-weights-c68": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser_all,
                content_page_parser=self.content_page_parser_all,
            ),
            "https://www.ukgymequipment.com/functional-fitness-c12": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser_all,
                content_page_parser=self.content_page_parser_all,
            ),
        }

        super().__init__(
            name="ukgymequipment",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
        )

    async def content_url_parser_all(self, url: str) -> List[str]:
        async with async_playwright() as playwright:
            page_number = 1
            # This scraper doesn't work well in headless mode
            browser = await playwright.chromium.launch(headless=False)
            page = await browser.new_page()
            res = []
            while True:
                await page.goto(f"{url}#page{page_number}")
                await page.wait_for_timeout(1000)
                try:
                    await page.get_by_title("next").nth(-1).scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    break
                html_source = await page.content()
                soup = BeautifulSoup(html_source, "html.parser")
                image_divs = soup.find_all("div", class_="product__image")
                res += [f"{url}/{i.find("a", class_="infclick").get("href")}" for i in image_divs]
                page_number += 1
            await browser.close()
        return list(set(res))

    async def content_page_parser_all(
        self, url: str, session: aiohttp.ClientSession
    ) -> ScrapedEquipment:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            raw_html = await response.text()
            soup = BeautifulSoup(raw_html, "html.parser")
            print(soup.prettify())
            brand = soup.find("span", class_="product-content__title--brand").text
            brand = re.sub(r"[\s\n]+", "", brand).strip()
            name = soup.find("span", id="js-product-title").text
            name = re.sub(r"[\n]+", "", name).strip()
            description = soup.find("div", id="product__description").text
            image_div = soup.find("div", class_="product__image__main")
            image_link = f"https://www.ukgymequipment.com{image_div.find("img").get("src")}"

            width = None
            length = None
            height = None
            weight_stack = None
            weight = None
            for p in soup.find("div", id="product__description").findAll("p"):
                if "Width" in p.text:
                    width = re.sub(r"Width:\s*", "", p.text)
                if "Length" in p.text:
                    length = re.sub(r"Length:\s*", "", p.text)
                if "Height" in p.text:
                    height = re.sub(r"Height:\s*", "", p.text)
                if "Weight Stack" in p.text:
                    weight_stack = re.sub(r"Weight Stack:\s*", "", p.text)
                if "Product Weight" in p.text:
                    weight = re.sub(r"Product Weight:\s*", "", p.text)

            return ScrapedEquipment(
                name=name,
                brand=brand,
                image_link=[image_link],
                description=description,
                sku=None,
                specification=EquipmentSpecification(
                    weight=weight,
                    height=height,
                    length=length,
                    width=width,
                    weight_stack=weight_stack,
                ),
            )
