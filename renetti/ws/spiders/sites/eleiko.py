import urllib.parse
from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class EleikoSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            url: ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
            for url in [
                "https://eleiko.com/en-gb/equipment/benches/competitionbenches",
                "https://eleiko.com/en-gb/equipment/benches/workoutbenches",
                "https://eleiko.com/en-gb/equipment/racksandrigs/rigs",
                "https://eleiko.com/en-gb/equipment/racksandrigs/racks",
                "https://eleiko.com/en-gb/equipment/strengthmachines/cables",
                "https://eleiko.com/en-gb/equipment/strengthmachines/handleattachments",
                "https://eleiko.com/en-gb/equipment/bars/weightlifting",
                "https://eleiko.com/en-gb/equipment/bars/powerlifting",
                "https://eleiko.com/en-gb/equipment/bars/hybridbars",
                "https://eleiko.com/en-gb/equipment/bars/specialty",
                "https://eleiko.com/en-gb/equipment/dumbbells/fixed",
                "https://eleiko.com/en-gb/equipment/dumbbells/rotating",
                "https://eleiko.com/en-gb/equipment/outdoor",
                "https://eleiko.com/en-gb/equipment/outdoor/galvanized",
                "https://eleiko.com/en-gb/equipment/functional-and-studio",
            ]
        }

        super().__init__(
            name="eleiko",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.PLAYWRIGHT,
        )
        self.base_url = "https://eleiko.com/"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url=url)
                await page.wait_for_timeout(2000)
                html = await page.content()
                soup = BeautifulSoup(markup=html, features="html.parser")
        return [
            f"{self.base_url}{a.get("href")}"
            for art in soup.find_all("article") or []
            for a in art.find_all("a") or []
        ]

    async def content_page_parser(
        self,
        url: str,
        browser: Browser,
        *args,
        **kwargs,
    ) -> ScrapedEquipment:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url=url)
                html = await page.content()
                soup = BeautifulSoup(markup=html)
                scraped_equipment = parse_product_json_ld_from_page(soup=soup)
                image_links = []
                for img in soup.findAll("img", class_="lg:group-hover:scale-103"):
                    raw_img_url = img.get("src").split("url=")[1]
                    img_url = urllib.parse.unquote(raw_img_url)
                    img_url = img_url.split("&")[0]
                    image_links.append(img_url)

                categories = url.split("/equipment")[1].split("/")[1:-1]
                description = soup.find_all("p", class_="lg:leading-normal")[0].text

                scraped_equipment["brands"] = ["eleiko"]
                scraped_equipment["image_links"] = image_links
                scraped_equipment["categories"] = categories
                scraped_equipment["description"] = description
        return scraped_equipment
