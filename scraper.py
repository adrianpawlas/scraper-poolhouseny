import asyncio
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Page


class PoolHouseScraper:
    def __init__(self):
        self.base_url = "https://poolhousenewyork.com"
        self.collection_urls = [
            f"{self.base_url}/collections/mens",
            f"{self.base_url}/collections/sale"
        ]
        self.browser = None
        self.context = None
        self.playwright = None

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def scroll_and_load_products(self, page: Page, max_products: int = 200) -> List[str]:
        urls = []
        seen = set()
        scroll_pause = 1.0

        while len(urls) < max_products:
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(scroll_pause)

            product_links = await page.query_selector_all("a[href*='/products/']")
            new_found = False

            for link in product_links:
                href = await link.get_attribute("href")
                if href and '/products/' in href and 'gift-card' not in href:
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                    if full_url not in seen:
                        seen.add(full_url)
                        urls.append(full_url)
                        new_found = True

            if not new_found and len(urls) > 0:
                await asyncio.sleep(0.5)
                product_links = await page.query_selector_all("a[href*='/products/']")
                for link in product_links:
                    href = await link.get_attribute("href")
                    if href and '/products/' in href and 'gift-card' not in href:
                        full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        if full_url not in seen:
                            seen.add(full_url)
                            urls.append(full_url)

            if len(urls) >= max_products:
                break

            scroll_pause = min(scroll_pause + 0.2, 2)

        return list(set(urls))[:max_products]

    async def scrape_collection(self, page: Page, url: str) -> List[str]:
        print(f"Scraping collection: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(3)

        product_links = await page.query_selector_all("a[href*='/products/']")
        urls = []
        seen = set()

        for link in product_links:
            href = await link.get_attribute("href")
            if href and '/products/' in href and 'gift-card' not in href:
                full_url = href if href.startswith('http') else f"{self.base_url}{href}"
                if full_url not in seen:
                    seen.add(full_url)
                    urls.append(full_url)

        print(f"Found {len(urls)} products on initial load")

        scroll_urls = await self.scroll_and_load_products(page, max_products=200)
        all_urls = list(set(urls + scroll_urls))

        print(f"Total products found: {len(all_urls)}")
        return all_urls

    async def scrape_all_collections(self) -> List[str]:
        await self.init_browser()
        page = await self.context.new_page()

        all_urls = []
        for collection_url in self.collection_urls:
            urls = await self.scrape_collection(page, collection_url)
            all_urls.extend(urls)
            await asyncio.sleep(2)

        unique_urls = list(set(all_urls))
        print(f"Total unique products: {len(unique_urls)}")
        return unique_urls

    async def get_product_data(self, url: str) -> Optional[dict]:
        if not self.browser:
            await self.init_browser()

        page = await self.context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            title = await self._get_title(page)
            price = await self._get_price(page)
            sale = await self._get_sale_price(page)
            description = await self._get_description(page)
            images = await self._get_images(page)
            category = await self._get_category(page)
            metadata = await self._get_metadata(page)
            sizes = await self._get_sizes(page)

            full_metadata = metadata
            if sizes:
                full_metadata = f"{metadata}\nSizes: {sizes}" if metadata else f"Sizes: {sizes}"

            product_data = {
                "source": "scraper-poolhouseny",
                "brand": "Pool House New York",
                "product_url": url,
                "title": title,
                "price": price,
                "sale": sale,
                "description": description,
                "category": category,
                "gender": "man",
                "second_hand": False,
                "image_url": images[0] if images else None,
                "additional_images": ", ".join(images[1:]) if len(images) > 1 else None,
                "metadata": full_metadata,
                "created_at": "NOW()"
            }

            return product_data

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            await page.close()

    async def _get_title(self, page: Page) -> str:
        try:
            title_el = await page.query_selector("h1")
            if title_el:
                return (await title_el.inner_text()).strip()
        except:
            pass
        return "Unknown"

    async def _get_price(self, page: Page) -> Optional[str]:
        try:
            price_container = await page.query_selector(".price")
            if price_container:
                price_text = await price_container.inner_text()
                price_text = price_text.replace("SOLD OUT", "").strip()
                return self._extract_prices(price_text)
        except:
            pass
        return None

    async def _get_sale_price(self, page: Page) -> Optional[str]:
        try:
            sale_el = await page.query_selector(".price-item--sale")
            if sale_el:
                sale_text = await sale_el.inner_text()
                return self._extract_prices(sale_text)

            price_container = await page.query_selector(".price")
            if price_container:
                items = await price_container.query_selector_all(".price-item")
                if len(items) > 1:
                    sale_text = await items[-1].inner_text()
                    return self._extract_prices(sale_text)
        except:
            pass
        return None

    def _extract_prices(self, text: str) -> str:
        text = text.strip()
        numbers = re.findall(r'[\d\s.,]+', text)
        currencies = re.findall(r'(USD|EUR|GBP|CZK|PLN|SEK|NOK|DKK|CAD|AUD|JPY|CNY|KRW|kr|€|£|¥)', text, re.IGNORECASE)

        if currencies and numbers:
            currency_map = {'kr': 'CZK', '€': 'EUR', '£': 'GBP', '¥': 'JPY'}
            currency = currencies[0].upper()
            currency = currency_map.get(currency, currency)
            number = numbers[0].replace(' ', '').replace(',', '.')
            return f"{number}{currency}"

        return text

    async def _get_description(self, page: Page) -> Optional[str]:
        try:
            desc_el = await page.query_selector(".product-description")
            if desc_el:
                return (await desc_el.inner_text()).strip()

            desc_el = await page.query_selector("[class*='description']")
            if desc_el:
                return (await desc_el.inner_text()).strip()
        except:
            pass
        return None

    async def _get_images(self, page: Page) -> List[str]:
        images = []
        try:
            img_elements = await page.query_selector_all(".product-gallery img, .product-image img, img[class*='product']")
            for img in img_elements:
                src = await img.get_attribute("src") or await img.get_attribute("data-src") or await img.get_attribute("data-srcset")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif not src.startswith("http"):
                        src = f"{self.base_url}{src}"

                    src = re.sub(r'\?.*$', '', src)

                    if src not in images and 'placeholder' not in src.lower():
                        images.append(src)
        except:
            pass

        if not images:
            try:
                main_img = await page.query_selector(".product-image img, .featured-image img")
                if main_img:
                    src = await main_img.get_attribute("src")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        images.append(src)
            except:
                pass

        return images

    async def _get_category(self, page: Page) -> Optional[str]:
        try:
            breadcrumb = await page.query_selector_all(".breadcrumb a, .breadcrumbs a, nav[role='navigation'] a")
            categories = []
            for crumb in breadcrumb:
                text = await crumb.inner_text()
                if text and text.strip() and text.strip() not in ['Home', 'All', 'Gift Cards']:
                    href = await crumb.get_attribute("href")
                    if href and '/collections/' in href:
                        categories.append(text.strip())

            if categories:
                return ", ".join(categories[:len(categories)//2] if len(categories) > 2 else categories)
        except:
            pass
        return None

    async def _get_metadata(self, page: Page) -> Optional[str]:
        try:
            details = []

            detail_elements = await page.query_selector_all(".product-details-content .text-body, .product-info .text-body")
            for el in detail_elements:
                text = await el.inner_text()
                if text and text.strip():
                    details.append(text.strip())

            accordion_items = await page.query_selector_all(".accordion-item")
            for item in accordion_items:
                title_el = await item.query_selector(".accordion-title")
                content_el = await item.query_selector(".accordion-content")
                if title_el and content_el:
                    title = await title_el.inner_text()
                    content = await content_el.inner_text()
                    if title and content:
                        details.append(f"{title}: {content.strip()}")

            return " | ".join(details) if details else None
        except:
            pass
        return None

    async def _get_sizes(self, page: Page) -> Optional[str]:
        try:
            size_buttons = await page.query_selector_all(".variant-option-label, .option-selection, [class*='size'] button")
            if size_buttons:
                sizes = []
                for btn in size_buttons:
                    text = await btn.inner_text()
                    if text and text.strip():
                        sizes.append(text.strip())
                return ", ".join(sizes) if sizes else None
        except:
            pass
        return None

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()