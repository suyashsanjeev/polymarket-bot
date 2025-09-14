import asyncio
import aiohttp
import random
from typing import List, Dict

# polymarket api endpoint for fetching active markets
BASE_API_URL = (
    "https://gamma-api.polymarket.com/events/pagination"
    "?limit={limit}&offset={offset}&active=true&archived=false&closed=false"
    "&order=creationDate&ascending=false"
)

DEFAULT_PAGE_SIZE = 500

# fetch a single page of markets from polymarket api
async def _fetch_page(session: aiohttp.ClientSession, offset: int, page_size: int):
    url = BASE_API_URL.format(limit=page_size, offset=offset)
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json()

# concurrently fetch markets from polymarket api
async def fetch_all_markets(page_size: int = DEFAULT_PAGE_SIZE, max_pages: int = 4):
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session:
        tasks = [
            asyncio.create_task(_fetch_page(session, off, page_size))
            for off in range(0, page_size * max_pages, page_size)
        ]
        pages: List[Dict] = await asyncio.gather(*tasks)

    data = []
    for page in pages:
        data.extend(page.get("data", []))

    return data

# extract market titles and slugs from api response data
def extract_markets(api_data: List[Dict]):
    markets = []
    for event in api_data:
        title = event.get("title", "").lower()
        slug = event.get("slug")
        if slug:
            markets.append((title, slug))
    return markets

# calculate exponential backoff delay with jitter for retries
def backoff_delay(base: int = 3, factor: float = 1.6, jitter: float = 0.3, attempt: int = 0):
    delay = base * (factor ** attempt)
    jitter_amt = delay * jitter
    return delay + random.uniform(-jitter_amt, jitter_amt)

