# I would say I'm decent at Python lol


import asyncio
import json
import math
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

client = ScrapflyClient(key="YOUR SCRAPFLY KEY", max_concurrency=2)
BASE_CONFIG = {
    # we want can select any country proxy:
    "country": "CA",
    # To see Glassdoor results of a specific country we must set a cookie:
    "cookies": {"tldp": "1"}
    # note: here are the other country codes:
    # 1: United States
    # 2: United Kingdom
    # 3: Canada (English)
    # 4: India
    # 5: Australia
    # 6: France
    # 7: Deutschland
    # 8: España
    # 9: Brasil
    # 10: Nederland
    # 11: Österreich
    # 12: México
    # 13: Argentina
    # 14: België (Nederlands)
    # 15: Belgique (Français)
    # 16: Schweiz (Deutsch)
    # 17: Suisse (Français)
    # 18: Ireland
    # 19: Canada (Français)
    # 20: Hong Kong
    # 21: New Zealand
    # 22: Singapore
    # 23: Italia
}


def find_json_objects(text: str, decoder=json.JSONDecoder()):
    """Find JSON objects in text, and generate decoded JSON data and it's ID"""
    pos = 0
    while True:
        match = text.find("{", pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            # backtrack to find the key/identifier for this json object:
            key_end = text.rfind('"', 0, match)
            key_start = text.rfind('"', 0, key_end)
            key = text[key_start + 1 : key_end]
            yield key, result
            pos = match + index
        except ValueError:
            pos = match + 1


def extract_apollo_state(result: ScrapeApiResponse) -> Dict:
    """Extract apollo graphql state data from HTML source"""
    data = re.findall('apolloState":\s*({.+})};', result.content)[0]
    return json.loads(data)


def extract_apollo_cache(result: ScrapeApiResponse) -> Dict[str, List]:
    """Extract apollo graphql cache data from HTML source"""
    script_with_cache = result.selector.xpath("//script[contains(.,'window.appCache')]/text()").get()
    cache = defaultdict(list)
    for key, data in find_json_objects(script_with_cache):
        cache[key].append(data)
    return cache


def parse_jobs(result: ScrapeApiResponse) -> Tuple[List[Dict], int]:
    """parse jobs page for job data and total amount of jobs"""
    cache = extract_apollo_cache(result)
    return [v["jobview"] for v in cache["JobListingSearchResult"]]


def parse_job_page_count(result: ScrapeApiResponse) -> int:
    """parse job page count from pagination details in Glassdoor jobs page"""
    total_results = result.selector.css(".paginationFooter::text").get()
    if not total_results:
        return 1
    total_results = int(total_results.split()[-1])
    total_pages = math.ceil(total_results / 40)
    return total_pages


def change_page(url: str, page: int) -> str:
    """update page number in a glassdoor url"""
    new = re.sub("(?:_P\d+)*.htm", f"_P{page}.htm", url)
    assert new != url
    return new


async def scrape_jobs(employer_id: str) -> List[Dict]:
    """Scrape job listings"""
    first_page_url = (
        f"https://www.glassdoor.com/Jobs/-Jobs-E{employer_id}_P1.htm?filter.countryId={BASE_CONFIG['cookies']['tldp']}"
    )
    first_page = await client.async_scrape(ScrapeConfig(url=first_page_url, **BASE_CONFIG))

    jobs = parse_jobs(first_page)
    total_pages = parse_job_page_count(first_page)

    print(f"scraped first page of jobs, scraping remaining {total_pages - 1} pages")
    other_pages = [
        ScrapeConfig(url=change_page(first_page.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in client.concurrent_scrape(other_pages):
        jobs.extend(parse_jobs(result))
    return jobs


def parse_reviews(result: ScrapeApiResponse) -> List[Dict]:
    """parse reviews page for review data"""
    cache = extract_apollo_state(result)
    xhr_cache = cache["ROOT_QUERY"]
    reviews = next(v for k, v in xhr_cache.items() if k.startswith("employerReviews") and v.get("reviews"))
    return reviews


async def scrape_reviews(employer_id: str) -> Dict:
    """Scrape reviews of a given company"""
    # scrape first page of jobs:
    first_page_url = f"https://www.glassdoor.com/Reviews/-Reviews-E{employer_id}_P1.htm?filter.countryId={BASE_CONFIG['cookies']['tldp']}"
    first_page = await client.async_scrape(ScrapeConfig(url=first_page_url))

    reviews = parse_reviews(first_page)
    total_pages = reviews["numberOfPages"]

    print(f"scraped first page of reviews, scraping remaining {total_pages - 1} pages")
    other_pages = [
        ScrapeConfig(url=change_page(first_page.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in client.concurrent_scrape(other_pages):
        reviews["reviews"].extend(parse_reviews(result)["reviews"])
    return reviews


def parse_salaries(result: ScrapeApiResponse) -> List[Dict]:
    """parse salary page for salary data"""
    cache = extract_apollo_state(result)
    xhr_cache = cache["ROOT_QUERY"]
    salaries = next(v for k, v in xhr_cache.items() if k.startswith("salariesByEmployer") and v.get("results"))
    return salaries


async def scrape_salaries(employer_id: str) -> Dict:
    """Scrape salary listings"""
    # scrape first page of jobs:
    first_page_url = f"https://www.glassdoor.com/Salaries/-Salaries-E{employer_id}_P1.htm?filter.countryId={BASE_CONFIG['cookies']['tldp']}"
    first_page = await client.async_scrape(ScrapeConfig(url=first_page_url))
    salaries = parse_salaries(first_page)
    total_pages = salaries["pages"]

    print(f"scraped first page of salaries, scraping remaining {total_pages - 1} pages")
    other_pages = [
        ScrapeConfig(url=change_page(first_page.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in client.concurrent_scrape(other_pages):
        salaries["results"].extend(parse_salaries(result)["results"])
    return salaries


if __name__ == "__main__":
    ebay_jobs_in_US = asyncio.run(scrape_jobs("7853"))
    ebay_reviews_in_US = asyncio.run(scrape_reviews("7853"))
    ebay_salaries_in_US = asyncio.run(scrape_salaries("7853"))
