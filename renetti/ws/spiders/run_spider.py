import asyncio

from renetti.ws.spiders import MatrixGymSpider

asyncio.run(MatrixGymSpider(request_batch_limit=20).crawl_website())
