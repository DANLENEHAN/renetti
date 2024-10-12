import asyncio

from renetti.ws.spiders.sites.technogym import TechnoGymSpider

asyncio.run(TechnoGymSpider(request_batch_limit=20).crawl_website())
