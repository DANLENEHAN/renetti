from enum import Enum
from typing import Callable, List, Optional, TypedDict


class RequestMethod(Enum):
    PLAYWRIGHT = "playwright"
    AIOHTTP = "aiohttp"


class EquipmentSpecification(TypedDict):
    weight: Optional[str]
    height: Optional[str]
    width: Optional[str]
    length: Optional[str]
    weight_stack: Optional[str]


class ScrapedEquipment(TypedDict):
    name: str
    image_link: List[str]
    brand: Optional[str]
    description: Optional[str]
    specification: EquipmentSpecification
    sku: Optional[str]  # https://www.barcodelookup.com/


class ListingUrlParsersMapper(TypedDict):
    content_url_parser: Callable
    content_page_parser: Callable
