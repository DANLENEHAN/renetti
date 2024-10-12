from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class UkGymEquipmentSpider(Spider):

    base_url: str

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
            content_request_method=RequestMethod.PLAYWRIGHT,
        )
        self.base_url = "https://www.ukgymequipment.com"

    async def content_url_parser_all(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                page_number = 1
                res = []
                while True:
                    await page.goto(f"{url}#page{page_number}")
                    await page.wait_for_timeout(1000)
                    try:
                        await page.get_by_title("next").nth(-1).scroll_into_view_if_needed(
                            timeout=3000
                        )
                    except Exception:
                        break
                    html_source = await page.content()
                    soup = BeautifulSoup(html_source, "html.parser")
                    search_results_list = soup.find("ul", id="js-search-results-products__list")
                    image_divs = search_results_list.find_all("div", class_="product__image")
                    res += [
                        f"{self.base_url}{i.find("a", class_="infclick").get("href")}"
                        for i in image_divs
                    ]
                    page_number += 1
        return list(set(res))

    async def content_page_parser_all(
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
        return parse_product_json_ld_from_page(soup=soup)
