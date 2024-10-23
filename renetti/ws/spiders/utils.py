import json
from typing import Any, Dict

from bs4 import BeautifulSoup

from renetti.ws.spiders.types import ScrapedEquipment


def parse_product_json_ld_from_page(soup: BeautifulSoup) -> ScrapedEquipment:

    product_information: Dict[str, Any] = {}

    # Find all script elements with type "application/ld+json"
    ld_script_elements = soup.find_all("script", type="application/ld+json")

    tried_normal_decode = False
    tried_remove_new_line_decode = False
    count = 0
    while count < len(ld_script_elements):
        elm = ld_script_elements[count]
        if not tried_normal_decode:
            json_text = elm.text
            tried_normal_decode = True
        else:
            json_text = elm.text.replace("\n", "")
            tried_remove_new_line_decode = True
        try:
            json_ld = json.loads(json_text)
            if isinstance(json_ld, list):
                # There shouldn't be more than one product
                # on a single page, if there is address uniquely
                json_ld = json_ld[0]
            # Check if the JSON-LD type is 'Product'
            if json_ld.get("@type") == "Product":
                product_information = json_ld
                break
            count += 1
        except json.JSONDecodeError:
            if tried_normal_decode and tried_remove_new_line_decode:
                tried_normal_decode = False
                tried_remove_new_line_decode = False
                count += 1

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
