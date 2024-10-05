import asyncio

from renetti.ws.spiders import GymEquipmentSpider

spider = GymEquipmentSpider()
asyncio.run(spider.crawl_website())
