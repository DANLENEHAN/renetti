from enum import Enum
from typing import Callable, List, Optional, TypedDict


class RequestMethod(Enum):
    PLAYWRIGHT = "playwright"
    AIOHTTP = "aiohttp"


class ScrapedEquipment(TypedDict):
    name: str
    image_links: List[str]
    mpn: Optional[str]
    description: Optional[str]
    brands: Optional[List[str]]
    categories: Optional[List[str]]
    skus: Optional[List[str]]  # https://www.barcodelookup.com/


class ListingUrlParsersMapper(TypedDict):
    content_url_parser: Callable
    content_page_parser: Callable
