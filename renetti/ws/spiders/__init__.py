import asyncio
import json
from typing import Callable, Dict, List, Optional, TypedDict

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


class EquipmentSpecification(TypedDict):
    weight: Optional[str]
    height: Optional[str]
    width: Optional[str]
    length: Optional[str]


class ScrapedEquipment(TypedDict):
    category: Optional[str]
    name: str
    image_link: str
    brand: Optional[str]
    description: Optional[str]
    specification: EquipmentSpecification
    sku: Optional[str]  # https://www.barcodelookup.com/


class ListingUrlParsersMapper(TypedDict):
    content_url_parser: Callable
    content_page_parser: Callable


class Spider:
    name: str
    file_path: str = "../../files"
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

    async def gather_content_links(self) -> Dict[str, List[str]]:
        print(f"(Scraper):({self.name}) - gathering content links")
        listing_url_content_links = {
            listing_url: asyncio.create_task(parsers["content_url_parser"](url=listing_url))
            for listing_url, parsers in self.listing_url_parser_mapper.items()
        }
        return {u: await task for u, task in listing_url_content_links.items()}

    def scrape_content_url(self, listing_url: str, content_url: str) -> asyncio.Task:
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
        return asyncio.create_task(parser_functions["content_page_parser"](url=content_url))

    async def scrape_content_links(self):
        print(f"(Scraper):({(self.name)}) - beginning content scraping")
        scrape_tasks = []
        for listing_url, content_urls in self.listing_url_content_links.items():
            for content_url in content_urls[:10]:
                scrape_tasks.append(
                    self.scrape_content_url(listing_url=listing_url, content_url=content_url)
                )
        return await asyncio.gather(*scrape_tasks, return_exceptions=True)

    def save_crawled_data(self):
        if self.listing_url_content_data:
            with open(f"{self.name}_crawled_data.json", "w") as f:
                print(f"(Scraper):({(self.name)}) - saving scraped data")
                f.write(json.dumps(self.listing_url_content_data, indent=3))
                exit(0)
        else:
            print(f"(Scraper):({(self.name)}) - has no data to save exiting")
            exit(1)

    async def crawl_website(self):
        self.listing_url_content_links = await self.gather_content_links()
        self.listing_url_content_data = await self.scrape_content_links()
        self.save_crawled_data()


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

    async def content_page_parser_all(self, url: str) -> ScrapedEquipment:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url)

            # Wait for the necessary element to load
            await page.wait_for_selector(".product.media")

            html_source = await page.content()
            soup = BeautifulSoup(html_source, "html.parser")

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
                category=None,
                brand=None,
                specification=EquipmentSpecification(
                    weight=None,
                    height=None,
                    length=None,
                    width=None,
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
            await browser.close()
        return scraped_equipment
