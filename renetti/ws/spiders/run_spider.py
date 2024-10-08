import asyncio

from renetti.ws.spiders.sites.uk_gym_equipment import UkGymEquipmentSpider

asyncio.run(UkGymEquipmentSpider(request_batch_limit=10).crawl_website())
