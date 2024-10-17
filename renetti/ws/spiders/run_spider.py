import asyncio

from renetti.ws.spiders import RogueFitnessSpider

asyncio.run(RogueFitnessSpider(request_batch_limit=20).crawl_website())
