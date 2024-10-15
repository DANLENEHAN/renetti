import asyncio
from typing import List, Optional

from bs4 import BeautifulSoup
from playwright.async_api import Browser

from renetti.ws.spiders.classes import Spider
from renetti.ws.spiders.types import ListingUrlParsersMapper, RequestMethod, ScrapedEquipment
from renetti.ws.spiders.utils import parse_product_json_ld_from_page


class MatrixGymSpider(Spider):

    base_url: str

    def __init__(self, request_batch_limit: Optional[int] = None):
        listing_group_parser_map = {
            url: ListingUrlParsersMapper(
                content_url_parser=self.content_url_parser,
                content_page_parser=self.content_page_parser,
            )
            for url in [
                "https://www.matrixfitness.com/uk/eng/cardio/catalog",
                "https://www.matrixfitness.com/uk/eng/group-training/catalog",
                "https://www.matrixfitness.com/uk/eng/home/catalog",
                "https://www.matrixfitness.com/uk/eng/strength/catalog",
            ]
        }

        super().__init__(
            name="matrixfitness",
            listing_group_parser_map=listing_group_parser_map,
            request_batch_limit=request_batch_limit,
            content_request_method=RequestMethod.PLAYWRIGHT,
        )
        self.base_url = "https://www.matrixfitness.com"

    async def content_url_parser(self, url: str, browser: Browser) -> List[str]:
        async with await browser.new_context() as context:
            async with await context.new_page() as page:
                await page.goto(url=url)
                await asyncio.sleep(5)
                urls = []
                button = page.locator(
                    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection"
                )
                if await button.is_visible():
                    await button.scroll_into_view_if_needed(timeout=3000)
                    await button.click()
                    await asyncio.sleep(5)

                while True:
                    html = await page.content()
                    soup = BeautifulSoup(markup=html, features="html.parser")
                    urls += [
                        f"{self.base_url}{a.get('href')}"
                        for a in soup.find("matrix-catalog-grid").findAll("a")
                        if a.get("href") is not None
                        and "onyx.matrixfitness.com" not in a.get("href")
                    ]

                    try:
                        button = page.locator("button.btn-primary")
                        if await button.is_visible():
                            await button.scroll_into_view_if_needed(timeout=3000)
                            await button.click()
                            await asyncio.sleep(5)
                        else:
                            break
                    except Exception:
                        break
        return list(set(urls))

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
                await page.wait_for_selector("div.product-gallery")
                html = await page.content()
                soup = BeautifulSoup(markup=html, features="html.parser")
                return parse_product_json_ld_from_page(soup=soup)
