from typing import List

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import EquipmentSpecification, ScrapedEquipment


class GymEquipmentSpider(Spider):
    def __init__(self):
        listing_url_parser_mapper = {
            "https://gymequipment.co.uk/strength-conditioning?product_list_limit=all": {
                "content_url_parser": self.content_url_parser_all,
                "content_page_parser": self.content_page_parser_all,
            }
        }
        super().__init__(
            name="gymequipment.co.uk", listing_url_parser_mapper=listing_url_parser_mapper
        )

    async def content_url_parser_all(self, url: str) -> List[str]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)
            await page.wait_for_selector(".product-item-photo")
            html_source = await page.content()
            soup = BeautifulSoup(html_source, "html.parser")
            a_elements = soup.find_all("a", class_="product-item-photo")
            await browser.close()
            return [a.get("href") for a in a_elements]

    async def content_page_parser_all(
        self, url: str, session: aiohttp.ClientSession
    ) -> ScrapedEquipment:
        async with session.get(url) as response:
            raw_html = await response.text()
            soup = BeautifulSoup(raw_html, "html.parser")
            equipment_title = soup.find("span", class_="base")
            equipment_description = soup.find("div", id="product.info.description")
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

            scraped_equipment = ScrapedEquipment(
                name=equipment_title.text if equipment_title else None,
                description=(equipment_description.text if equipment_description else None),
                image_link=equipment_image_link,
                brand=None,
                specification=EquipmentSpecification(
                    weight=None,
                    height=None,
                    length=None,
                    width=None,
                    weight_stack=None,
                ),
                sku=None,
            )
            equipment_specifications = soup.find("table", id="product-attribute-specs-table")
            if equipment_specifications:
                for td, tr in list(
                    zip(
                        equipment_specifications.findAll("td"),
                        equipment_specifications.findAll("tr"),
                    )
                ):
                    if "SKU" in tr.text:
                        scraped_equipment["sku"] = td.text
                    elif "Weight" in tr.text:
                        scraped_equipment["specification"]["weight"] = td.text
                    elif "Height" in tr.text:
                        scraped_equipment["specification"]["height"] = td.text
                    elif "Length" in tr.text:
                        scraped_equipment["specification"]["length"] = td.text
                    elif "Width" in tr.text:
                        scraped_equipment["specification"]["width"] = td.text
        return scraped_equipment
