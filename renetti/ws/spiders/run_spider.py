import asyncio

from renetti.ws.spiders.sites.uk_gym_equipment import UkGymEquipmentSpider

# asyncio.run(GymEquipmentSpider().crawl_website())
asyncio.run(UkGymEquipmentSpider(request_batch_limit=1).crawl_website())
