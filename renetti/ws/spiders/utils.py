import json
from typing import Any, Dict

from bs4 import BeautifulSoup

from renetti.ws.spiders.types import ScrapedEquipment


def parse_product_json_ld_from_page(soup: BeautifulSoup) -> ScrapedEquipment:

    product_information: Dict[str, Any] = {}

    # Find all script elements with type "application/ld+json"
    ld_script_elements = soup.find_all("script", type="application/ld+json")

    for elm in ld_script_elements:
        try:
            json_ld = json.loads(elm.text)
            # Check if the JSON-LD type is 'Product'
            if json_ld.get("@type") == "Product":
                product_information = json_ld
                break
        except json.JSONDecodeError:
            continue  # Ignore JSON decode errors

    if not product_information:
        raise ValueError("No Product Found")

    # Keys can be capped or not capped it seems
    product_information = {k.lower(): v for k, v in product_information.items()}

    name = product_information["name"]

    # Not always present in the json-ld
    product_image = product_information.get("image")
    image_links = []
    if product_image:
        image_links = product_image if isinstance(product_image, list) else [product_image]

    # Optional Fields
    product_brand = product_information.get("brand")
    brands = []
    if product_brand:
        product_brands = product_brand if isinstance(product_brand, list) else [product_brand]
        brands = [b.get("name") or b.get("Name") for b in product_brands]

    description = product_information.get("description")

    product_category = product_information.get("category")
    categories = []
    if product_category:
        categories = product_category if isinstance(product_category, list) else [product_category]

    mpn = product_information.get("mpn")

    skus = []
    product_sku = product_information.get("sku")
    if product_sku:
        skus = product_sku if isinstance(product_sku, list) else [product_sku]

    product_offers = product_information.get("offers")
    if product_offers:
        product_offers = product_offers if isinstance(product_offers, list) else [product_offers]
        for offer in product_offers:
            sku = offer.get("sku") or offer.get("Sku")
            if sku:
                skus.append(sku)

    return ScrapedEquipment(
        name=name,
        image_links=list(set(image_links)),
        mpn=mpn,
        description=description,
        brands=list(set(brands)),
        categories=list(set(categories)),
        skus=list(set(skus)),
    )
