import asyncio

from renetti.ws.spiders.sites.uk_gym_equipment import UkGymEquipmentSpider

asyncio.run(UkGymEquipmentSpider().crawl_website())
