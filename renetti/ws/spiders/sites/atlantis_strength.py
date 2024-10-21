from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment


class AtlantisStrengthSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            "https://atlantisstrength.com/gym-equipment/": ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
        }

        super().__init__(
            name="atlantisstrength",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.PLAYWRIGHT,
        )
        self.base_url = "https://atlantisstrength.com"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                urls = []
                await page.goto(url=url)
                while True:
                    await page.wait_for_timeout(3000)
                    button = await page.wait_for_selector(
                        "button.c-Pagination__content--next", timeout=2000, state="visible"
                    )
                    await button.scroll_into_view_if_needed()
                    html = await page.content()
                    soup = BeautifulSoup(markup=html, features="html.parser")
                    a_tags = soup.findAll("a", class_="c-equipCards")
                    urls += [a.get("href") for a in a_tags]
                    await page.wait_for_timeout(1000)
                    await button.click()
                    if await button.is_disabled():
                        await page.wait_for_timeout(2000)
                        break
        return urls

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
                await page.wait_for_timeout(2000)
                html = await page.content()
                soup = BeautifulSoup(markup=html, features="html.parser")

                name = soup.find("div", class_="c-headerEquipment__contentCol--title")
                if name:
                    name = name.find("h2").text
                else:
                    raise ValueError("Can't find equipment name on page")

                image_divs = soup.findAll("div", class_="c-headerEquipment__slider--slides__img")
                image_links = []
                if image_divs:
                    image_links = [d.find("img").get("src") for d in image_divs]
                else:
                    raise ValueError("Can't find equipment images on page")

                category_divs = soup.find(
                    "div", class_="c-headerEquipment__contentCol--equipmentInfos"
                )
                categories = []
                if category_divs:
                    categories = [
                        a.text.replace("\n", "").strip() for a in category_divs.findAll("a")
                    ]
                else:
                    raise ValueError("Can't find equipment categories on tge page")

                description = soup.find("div", class_="Editable")
                if description:
                    description = " ".join(
                        [line for line in description.text.split("\n") if line != ""]
                    )
                else:
                    raise ValueError("Can't find equipment description on the page")
        return ScrapedEquipment(
            name=name,
            image_links=image_links,
            mpn=None,
            skus=None,
            brands=["Atlantis"],
            categories=categories,
            description=description,
        )
