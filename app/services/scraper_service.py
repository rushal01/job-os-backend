"""Job scraper service — real scrapers for multiple job sources."""

import asyncio
import re
import time
from html import unescape

import httpx
from loguru import logger

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    logger.warning("beautifulsoup4 not installed — HTML scraping disabled")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; JobOS/1.0; +https://github.com/job-os)"
    ),
    "Accept": "application/json, text/html, */*",
}
_RATE_LIMIT_DELAY = 1.0  # seconds between requests per source

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_html(html_str: str | None) -> str:
    """Strip HTML tags, returning plain text."""
    if not html_str:
        return ""
    if BeautifulSoup is not None:
        return BeautifulSoup(html_str, "html.parser").get_text(separator=" ", strip=True)
    # Fallback: naive tag removal
    return unescape(re.sub(r"<[^>]+>", " ", html_str)).strip()


def _empty_job() -> dict:
    """Return a blank job dict with all expected keys."""
    return {
        "title": "",
        "company": "",
        "location": None,
        "location_type": None,
        "seniority": None,
        "employment_type": None,
        "description": None,
        "apply_url": None,
        "source": "",
        "source_url": None,
        "posted_date": None,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": None,
        "skills_required": [],
        "skills_preferred": [],
    }


def _infer_seniority(title: str) -> str | None:
    """Guess seniority from a job title string."""
    t = title.lower()
    if any(w in t for w in ("intern",)):
        return "Intern"
    if any(w in t for w in ("junior", "jr.", "jr ", "entry")):
        return "Junior"
    if any(w in t for w in ("senior", "sr.", "sr ", "lead", "principal", "staff")):
        return "Senior"
    if any(w in t for w in ("manager", "director", "vp ", "head of", "chief")):
        return "Manager"
    return "Mid"


def _infer_location_type(text: str) -> str | None:
    """Guess remote/onsite/hybrid from text."""
    t = text.lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    if "on-site" in t or "onsite" in t or "in-office" in t:
        return "onsite"
    return None


def _parse_salary(text: str | None) -> tuple[int | None, int | None, str | None]:
    """Try to extract salary range from a string. Returns (min, max, currency)."""
    if not text:
        return None, None, None
    # Match patterns like $100k-$150k, $100,000 - $150,000, 100k-150k
    currency = "USD"
    if "\u00a3" in text:
        currency = "GBP"
    elif "\u20ac" in text:
        currency = "EUR"

    numbers = re.findall(r"[\d,]+(?:\.\d+)?[kK]?", text)
    parsed: list[int] = []
    for n in numbers:
        n_clean = n.replace(",", "")
        if n_clean.lower().endswith("k"):
            parsed.append(int(float(n_clean[:-1]) * 1000))
        else:
            val = int(float(n_clean))
            if val > 1000:  # looks like a salary
                parsed.append(val)
    if len(parsed) >= 2:
        return min(parsed[:2]), max(parsed[:2]), currency
    if len(parsed) == 1:
        return parsed[0], None, currency
    return None, None, None


# ===================================================================
# RemoteOK scraper
# ===================================================================
async def scrape_remoteok(
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Fetch remote jobs from RemoteOK's public JSON API."""
    jobs: list[dict] = []
    url = "https://remoteok.com/api"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        # First element is metadata, skip it
        listings = data[1:] if isinstance(data, list) and len(data) > 1 else []

        kw_lower = [k.lower() for k in keywords] if keywords else []

        for item in listings:
            # Filter by keywords if provided
            title = item.get("position", "")
            company = item.get("company", "")
            desc = item.get("description", "")
            tags = [t.lower() for t in item.get("tags", [])]
            combined = f"{title} {company} {desc} {' '.join(tags)}".lower()

            if kw_lower and not any(kw in combined for kw in kw_lower):
                continue

            sal_min, sal_max, sal_cur = None, None, None
            if item.get("salary_min"):
                sal_min = int(item["salary_min"]) if str(item["salary_min"]).isdigit() else None
            if item.get("salary_max"):
                sal_max = int(item["salary_max"]) if str(item["salary_max"]).isdigit() else None
            if sal_min or sal_max:
                sal_cur = "USD"

            posted = None
            if item.get("date"):
                try:
                    posted = item["date"]  # ISO format from API
                except Exception:
                    pass

            job = _empty_job()
            job.update({
                "title": title,
                "company": company,
                "location": item.get("location") or "Remote",
                "location_type": "remote",
                "seniority": _infer_seniority(title),
                "employment_type": "Full-time",
                "description": _strip_html(desc),
                "apply_url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                "source": "remoteok",
                "source_url": f"https://remoteok.com/remote-jobs/{item.get('id', '')}",
                "posted_date": posted,
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": sal_cur,
                "skills_required": item.get("tags", [])[:10],
                "skills_preferred": [],
            })
            jobs.append(job)

        logger.info(f"RemoteOK: fetched {len(jobs)} jobs matching keywords={keywords}")
    except Exception as exc:
        logger.error(f"RemoteOK scraper failed: {exc}")

    return jobs


# ===================================================================
# HackerNews "Who is Hiring?" scraper
# ===================================================================
_HN_API = "https://hacker-news.firebaseio.com/v0"


async def scrape_hn_hiring(
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Scrape the latest HN 'Who is Hiring?' thread."""
    jobs: list[dict] = []

    try:
        thread_id = await _find_hn_hiring_thread()
        if not thread_id:
            logger.warning("HN: could not find a recent 'Who is Hiring?' thread")
            return jobs

        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            # Get thread to find kid IDs (top-level comments)
            resp = await client.get(f"{_HN_API}/item/{thread_id}.json")
            resp.raise_for_status()
            thread = resp.json()
            kid_ids = thread.get("kids", [])

            kw_lower = [k.lower() for k in keywords] if keywords else []

            # Fetch comments in batches (limit to first 200 to be reasonable)
            for batch_start in range(0, min(len(kid_ids), 200), 20):
                batch = kid_ids[batch_start : batch_start + 20]
                tasks = [
                    client.get(f"{_HN_API}/item/{cid}.json")
                    for cid in batch
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for r in responses:
                    if isinstance(r, Exception):
                        continue
                    try:
                        r.raise_for_status()
                        comment = r.json()
                    except Exception:
                        continue

                    if not comment or comment.get("deleted") or comment.get("dead"):
                        continue

                    text = comment.get("text", "")
                    plain = _strip_html(text)

                    if kw_lower and not any(kw in plain.lower() for kw in kw_lower):
                        continue

                    parsed = _parse_hn_comment(plain, comment.get("id"))
                    if parsed:
                        jobs.append(parsed)

                # Rate limit between batches
                await asyncio.sleep(_RATE_LIMIT_DELAY)

        logger.info(f"HN Hiring: fetched {len(jobs)} jobs matching keywords={keywords}")
    except Exception as exc:
        logger.error(f"HN Hiring scraper failed: {exc}")

    return jobs


async def _find_hn_hiring_thread() -> int | None:
    """Find the most recent 'Who is Hiring?' thread by searching whoishiring submissions."""
    try:
        # whoishiring is the bot that posts monthly threads — user ID 10325685
        # We use the Algolia HN search API to find the latest thread
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            params = {
                "query": "Ask HN: Who is hiring?",
                "tags": "story",
                "hitsPerPage": 5,
                "numericFilters": "created_at_i>{}".format(
                    int(time.time()) - 60 * 86400  # last 60 days
                ),
            }
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search", params=params
            )
            resp.raise_for_status()
            data = resp.json()

            for hit in data.get("hits", []):
                title = hit.get("title", "")
                if "who is hiring" in title.lower() and hit.get("objectID"):
                    return int(hit["objectID"])
    except Exception as exc:
        logger.error(f"HN thread search failed: {exc}")
    return None


def _parse_hn_comment(text: str, comment_id: int | None) -> dict | None:
    """Parse a top-level HN hiring comment into a job dict.

    Convention: first line = "Company | Location | Role | …"
    """
    lines = text.strip().split("\n")
    if not lines:
        return None

    header = lines[0]
    parts = [p.strip() for p in header.split("|")]

    company = parts[0] if len(parts) >= 1 else ""
    loc = parts[1] if len(parts) >= 2 else None
    title = parts[2] if len(parts) >= 3 else "Software Engineer"

    if not company:
        return None

    description = "\n".join(lines[1:]).strip() if len(lines) > 1 else header

    # Try to find URL in the text
    url_match = re.search(r"https?://\S+", text)
    apply_url = url_match.group(0).rstrip(".,;)") if url_match else None

    sal_min, sal_max, sal_cur = _parse_salary(text)

    job = _empty_job()
    job.update({
        "title": title.strip() if title else "Software Engineer",
        "company": company.strip(),
        "location": loc.strip() if loc else None,
        "location_type": _infer_location_type(f"{loc or ''} {header}"),
        "seniority": _infer_seniority(title or header),
        "employment_type": "Full-time",
        "description": description,
        "apply_url": apply_url,
        "source": "hn_hiring",
        "source_url": f"https://news.ycombinator.com/item?id={comment_id}" if comment_id else None,
        "posted_date": None,
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_currency": sal_cur,
        "skills_required": [],
        "skills_preferred": [],
    })
    return job


# ===================================================================
# Adzuna scraper
# ===================================================================
async def scrape_adzuna(
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Fetch jobs from the Adzuna API. Requires app_id and app_key in config."""
    jobs: list[dict] = []
    config = config or {}
    app_id = config.get("adzuna_app_id") or config.get("ADZUNA_APP_ID")
    app_key = config.get("adzuna_app_key") or config.get("ADZUNA_APP_KEY")
    country = config.get("adzuna_country", "us")

    if not app_id or not app_key:
        logger.warning("Adzuna: missing app_id or app_key in config — skipping")
        return jobs

    query = " ".join(keywords) if keywords else "software engineer"
    base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    try:
        params: dict = {
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "results_per_page": 50,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location

        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = await client.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("results", []):
            sal_min = None
            sal_max = None
            if item.get("salary_min"):
                sal_min = int(item["salary_min"])
            if item.get("salary_max"):
                sal_max = int(item["salary_max"])
            sal_cur = "GBP" if country == "gb" else "USD"

            posted = None
            if item.get("created"):
                try:
                    posted = item["created"]
                except Exception:
                    pass

            title = item.get("title", "")
            loc_str = item.get("location", {}).get("display_name")

            job = _empty_job()
            job.update({
                "title": _strip_html(title),
                "company": item.get("company", {}).get("display_name", ""),
                "location": loc_str,
                "location_type": _infer_location_type(f"{title} {loc_str or ''} {item.get('description', '')}"),
                "seniority": _infer_seniority(title),
                "employment_type": item.get("contract_type") or "Full-time",
                "description": _strip_html(item.get("description", "")),
                "apply_url": item.get("redirect_url"),
                "source": "adzuna",
                "source_url": item.get("redirect_url"),
                "posted_date": posted,
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": sal_cur if (sal_min or sal_max) else None,
                "skills_required": [],
                "skills_preferred": [],
            })
            jobs.append(job)

        logger.info(f"Adzuna: fetched {len(jobs)} jobs for query='{query}'")
    except Exception as exc:
        logger.error(f"Adzuna scraper failed: {exc}")

    return jobs


# ===================================================================
# GitHub Jobs scraper (scrapes github.com/about/careers and repos)
# ===================================================================
async def scrape_github_jobs(
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Scrape job listings from GitHub's careers page and related sources.

    Since the old GitHub Jobs API is defunct, we scrape:
    - github.com/about/careers filtered pages
    - Popular job-listing repos
    """
    jobs: list[dict] = []

    if BeautifulSoup is None:
        logger.warning("GitHub Jobs: beautifulsoup4 not installed — skipping")
        return jobs

    query = "+".join(keywords) if keywords else "software+engineer"

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True
        ) as client:
            # ---------- GitHub Careers page ----------
            url = f"https://www.github.careers/careers-home/jobs?page=1&query={query}"
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Parse job cards — GitHub careers uses js-rendered content,
                    # so we try common selectors
                    for card in soup.select("a[href*='/jobs/']"):
                        title = card.get_text(strip=True)
                        href = card.get("href", "")
                        if not title or len(title) < 5:
                            continue
                        if not href.startswith("http"):
                            href = f"https://www.github.careers{href}"

                        job = _empty_job()
                        job.update({
                            "title": title,
                            "company": "GitHub",
                            "location": location,
                            "location_type": _infer_location_type(title),
                            "seniority": _infer_seniority(title),
                            "employment_type": "Full-time",
                            "description": None,
                            "apply_url": href,
                            "source": "github_jobs",
                            "source_url": href,
                        })
                        jobs.append(job)
            except Exception as exc:
                logger.debug(f"GitHub careers page scrape failed: {exc}")

            await asyncio.sleep(_RATE_LIMIT_DELAY)

            # ---------- Popular repos that aggregate job listings ----------
            # e.g. https://github.com/poteto/hiring-without-whiteboards (README)
            repo_url = "https://raw.githubusercontent.com/poteto/hiring-without-whiteboards/main/README.md"
            try:
                resp = await client.get(repo_url)
                if resp.status_code == 200:
                    kw_lower = [k.lower() for k in keywords] if keywords else []
                    # Parse markdown table rows: | [Company](url) | ... |
                    for line in resp.text.split("\n"):
                        if not line.startswith("|"):
                            continue
                        cells = [c.strip() for c in line.split("|")]
                        if len(cells) < 3:
                            continue
                        # first cell after | is company link
                        link_match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cells[1])
                        if not link_match:
                            continue

                        company = link_match.group(1)
                        apply_url = link_match.group(2)
                        # cells[2] is usually the location
                        loc = cells[2] if len(cells) > 2 else None

                        combined = f"{company} {loc or ''}".lower()
                        if kw_lower and not any(kw in combined for kw in kw_lower):
                            continue

                        job = _empty_job()
                        job.update({
                            "title": "Software Engineer",
                            "company": company,
                            "location": loc,
                            "location_type": _infer_location_type(loc or ""),
                            "seniority": None,
                            "employment_type": "Full-time",
                            "description": "Listed on hiring-without-whiteboards",
                            "apply_url": apply_url,
                            "source": "github_jobs",
                            "source_url": apply_url,
                        })
                        jobs.append(job)
            except Exception as exc:
                logger.debug(f"GitHub repo scrape failed: {exc}")

        logger.info(f"GitHub Jobs: fetched {len(jobs)} listings")
    except Exception as exc:
        logger.error(f"GitHub Jobs scraper failed: {exc}")

    return jobs


# ===================================================================
# Generic web scraper
# ===================================================================
async def scrape_web_generic(
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Generic HTML scraper for configurable job board URLs.

    Config keys:
        urls: list[str] — pages to scrape
        selectors: dict — CSS selectors for job cards and fields:
            card: str — selector for each job card container
            title: str — selector within card for title
            company: str — selector within card for company
            location: str — selector within card for location
            link: str — selector within card for apply link (href)
            description: str — selector within card for description
    """
    jobs: list[dict] = []
    config = config or {}

    if BeautifulSoup is None:
        logger.warning("Web scraper: beautifulsoup4 not installed — skipping")
        return jobs

    urls: list[str] = config.get("urls", [])
    selectors: dict = config.get("selectors", {})

    # Defaults — work for many simple job boards
    card_sel = selectors.get("card", ".job-listing, .job-card, .job-post, article.job")
    title_sel = selectors.get("title", "h2, h3, .job-title, .title")
    company_sel = selectors.get("company", ".company, .company-name, .employer")
    location_sel = selectors.get("location", ".location, .job-location")
    link_sel = selectors.get("link", "a[href]")
    desc_sel = selectors.get("description", ".description, .job-description, p")

    if not urls:
        logger.debug("Web scraper: no URLs configured — skipping")
        return jobs

    kw_lower = [k.lower() for k in keywords] if keywords else []

    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True
    ) as client:
        for page_url in urls:
            try:
                resp = await client.get(page_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                cards = soup.select(card_sel)
                for card in cards:
                    title_el = card.select_one(title_sel)
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    company_el = card.select_one(company_sel)
                    company = company_el.get_text(strip=True) if company_el else ""

                    loc_el = card.select_one(location_sel)
                    loc = loc_el.get_text(strip=True) if loc_el else location

                    link_el = card.select_one(link_sel)
                    href = link_el.get("href", "") if link_el else ""
                    if href and not href.startswith("http"):
                        # Make absolute
                        from urllib.parse import urljoin
                        href = urljoin(page_url, href)

                    desc_el = card.select_one(desc_sel)
                    desc = desc_el.get_text(strip=True) if desc_el else None

                    combined = f"{title} {company} {desc or ''}".lower()
                    if kw_lower and not any(kw in combined for kw in kw_lower):
                        continue

                    job = _empty_job()
                    job.update({
                        "title": title,
                        "company": company or "Unknown",
                        "location": loc,
                        "location_type": _infer_location_type(f"{title} {loc or ''}"),
                        "seniority": _infer_seniority(title),
                        "employment_type": "Full-time",
                        "description": desc,
                        "apply_url": href or page_url,
                        "source": "web",
                        "source_url": href or page_url,
                    })
                    jobs.append(job)

                logger.debug(f"Web scraper: {len(cards)} cards found on {page_url}")
            except Exception as exc:
                logger.error(f"Web scraper failed for {page_url}: {exc}")

            await asyncio.sleep(_RATE_LIMIT_DELAY)

    logger.info(f"Web scraper: fetched {len(jobs)} jobs total from {len(urls)} URLs")
    return jobs


# ===================================================================
# Dispatcher
# ===================================================================
_SCRAPERS: dict[str, object] = {
    "remoteok": scrape_remoteok,
    "hn_hiring": scrape_hn_hiring,
    "adzuna": scrape_adzuna,
    "github_jobs": scrape_github_jobs,
    "web": scrape_web_generic,
}


async def scrape_sources(
    sources: list[str],
    keywords: list[str],
    location: str | None = None,
    config: dict | None = None,
) -> list[dict]:
    """Dispatch to scrapers based on source names, aggregate results.

    Args:
        sources: List of source identifiers (e.g. ["remoteok", "adzuna"]).
        keywords: Search keywords.
        location: Optional location filter.
        config: Dict with API keys and other scraper-specific settings.

    Returns:
        Combined list of raw job dicts from all sources.
    """
    all_jobs: list[dict] = []

    for source in sources:
        scraper = _SCRAPERS.get(source)
        if scraper is None:
            if source == "mock":
                logger.debug("Skipping mock source in scrape_sources")
                continue
            logger.warning(f"Unknown scraper source: {source}")
            continue

        logger.info(f"Running scraper: {source}")
        try:
            result = await scraper(keywords=keywords, location=location, config=config)  # type: ignore[operator]
            all_jobs.extend(result)
        except Exception as exc:
            logger.error(f"Scraper '{source}' raised unexpected error: {exc}")

    logger.info(f"scrape_sources: {len(all_jobs)} total jobs from {len(sources)} sources")
    return all_jobs
