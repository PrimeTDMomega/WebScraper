# Job Listing Scraper
This script uses the Scrapfly library, asyncio and json to scrape job listings from the Glassdoor website. The script sets up a ScrapflyClient object with the user's API key and a maximum concurrency of 2, and defines a number of functions to extract and parse data from the Glassdoor website using the Scrapfly library.

## Scraping Job Listings
The scrape_jobs function uses the asyncio library to asynchronously scrape job listings for a given employer ID and returns a list of job listings. The function starts by fetching the first page of job listings for the given employer ID and passing it to the parse_jobs function to extract the job data.

```
#!/usr/bin/python
async def scrape_jobs(employer_id: str) -> List[Dict]:
    """Scrape job listings"""
    first_page_url = f"https://www.glassdoor.com/job-listing/{employer_id}-jobs-SRCH_IL.0,{employer_id}_IP"
    result = await client.scrape(first_page_url, BASE_CONFIG)
    jobs = parse_jobs(result)

```
#!/usr/bin/python
The script then uses the parse_job_page_count function to determine the total number of pages of job listings available, and uses the change_page function to generate URLs for each page of job listings. The script then uses the asyncio gather function to scrape all pages of job listings in parallel, and the extend method to add the job listings from each page to the jobs list.

```
#!/usr/bin/python
    total_pages = parse_job_page_count(result)
    tasks = [client.scrape(change_page(first_page_url, page), BASE_CONFIG) for page in range(2, total_pages + 1)]
    results = await asyncio.gather(*tasks)
    for result in results:
        jobs.extend(parse_jobs(result))
```

## Extracting and Parsing Data
The extract_apollo_state function is used to extract the Apollo GraphQL state data from the HTML source of a Glassdoor job listing page.

```
#!/usr/bin/python
def extract_apollo_state(result: ScrapeApiResponse) -> Dict:
    """Extract apollo graphql state data from HTML source"""
    data = re.findall('apolloState":\s*({.+})};', result.content)[0]
    return json.loads(data)
```

The extract_apollo_cache function is used to extract the Apollo GraphQL cache data from the HTML source of a Glassdoor job listing page.

```
#!/usr/bin/python
def extract_apollo_cache(result: ScrapeApiResponse) -> Dict[str, List]:
    """Extract apollo graphql cache data from HTML source"""
    script_with_cache = result.selector.xpath("//script[contains(.,'window.appCache')]/text()").get()
    cache = defaultdict(list)
    for key, data in find_json_objects(
```
