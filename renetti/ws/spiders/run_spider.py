import asyncio

from renetti.ws.spiders import AtlantisStrengthSpider

asyncio.run(AtlantisStrengthSpider(request_batch_limit=20).crawl_website())
