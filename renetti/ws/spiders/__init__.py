import json
from typing import Any, Dict, List


class Spider:
    base_url: str
    name: str

    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name

    def crawl_site(self) -> Dict[str, Any]:
        raise NotImplementedError

    def save_crawled_data(self, data: List[Dict[str, Any]]):
        with open(f"{self.name}_crawled_data.json") as f:
            f.write(json.dumps(data, indent=3))


class GymEquipment(Spider):

    def crawl_site(self) -> Dict[str, Any]:
        return super().crawl_site()
