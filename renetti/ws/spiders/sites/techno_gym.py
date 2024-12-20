import asyncio
from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class TechnoGymSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            url: ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
            for url in [
                "https://www.technogym.com/en-GB/category/exercise-tools/",
                "https://www.technogym.com/en-GB/category/barbells/",
                "https://www.technogym.com/en-GB/category/benches/",
                "https://www.technogym.com/en-GB/category/cable-stations/",
                "https://www.technogym.com/en-GB/category/dumbbells-weights/",
                "https://www.technogym.com/en-GB/category/ellipticals-and-cross-trainers/",
                "https://www.technogym.com/en-GB/category/exercise-bikes/",
                "https://www.technogym.com/en-GB/category/flexibility-stretching/",
                "https://www.technogym.com/en-GB/category/multigyms/",
                "https://www.technogym.com/en-GB/category/plate-loaded/",
                "https://www.technogym.com/en-GB/category/racks/",
                "https://www.technogym.com/en-GB/category/rowers/",
                "https://www.technogym.com/en-GB/category/selectorised/",
                "https://www.technogym.com/en-GB/category/stair-climbers/",
                "https://www.technogym.com/en-GB/category/treadmills/",
                "https://www.technogym.com/en-GB/category/upper-body-trainers/",
                "https://www.technogym.com/en-GB/category/weight-racks/",
            ]
        }

        super().__init__(
            name="technogym",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.PLAYWRIGHT,
        )
        self.base_url = "https://www.technogym.com"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url)
                await page.wait_for_timeout(1000)
                while True:
                    try:
                        button = await page.wait_for_selector("button.css-1v8s6ns", timeout=5000)
                        await button.scroll_into_view_if_needed()
                        await button.click()
                    except Exception:
                        break
                    await asyncio.sleep(1)

                html_content = await page.content()
                soup = BeautifulSoup(markup=html_content)
                return [
                    f"{self.base_url}{a.get("href")}"
                    for a in soup.findAll("a", class_="css-1jke4yk")
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

                glb_frame = None
                glb_image = None
                for frame in page.frames:
                    if "londondynamics.com" in frame.url:
                        glb_frame = frame
                        await glb_frame.wait_for_selector("model-viewer")
                        break

                if glb_frame:
                    frame_content = await glb_frame.content()
                    frame_soup = BeautifulSoup(markup=frame_content)
                    model_viewer = frame_soup.find("model-viewer")
                    if model_viewer:
                        glb_image = model_viewer.get("src")

                if glb_image:
                    scraped_equipment["image_links"].append(glb_image)
        return scraped_equipment
