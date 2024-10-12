import asyncio

from renetti.ws.spiders import (
    TechnoGymSpider,
)

asyncio.run(TechnoGymSpider(request_batch_limit=10).crawl_website())
