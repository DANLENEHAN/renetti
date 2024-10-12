import asyncio

from renetti.ws.spiders import LifeFitnessSpider

asyncio.run(LifeFitnessSpider(request_batch_limit=20).crawl_website())
