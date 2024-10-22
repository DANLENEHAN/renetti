import asyncio

from renetti.ws.spiders import EleikoSpider

asyncio.run(EleikoSpider(request_batch_limit=5).crawl_website())
