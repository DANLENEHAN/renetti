import asyncio

from renetti.ws.spiders import HoistFitnessSpider

asyncio.run(HoistFitnessSpider(request_batch_limit=20).crawl_website())
