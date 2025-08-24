#!/usr/bin/env python3

"""
KodeKloud Fast Hybrid Scraper
=============================

Optimized scraper that combines:
1. Playwright for course discovery and navigation expansion (handles JavaScript)
2. Parallel HTTP requests for fast content extraction

This approach is much faster than pure Playwright while maintaining comprehensive discovery.
"""

import asyncio
import csv
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, BrowserContext
import threading

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KodeKloudScraper:
    """High-performance hybrid scraper combining Playwright discovery with HTTP extraction."""
    
    def __init__(self, max_workers: int = 16, headless: bool = True):
        self.base_url = "https://notes.kodekloud.com"
        self.max_workers = max_workers
        self.headless = headless
        self.session_lock = threading.Lock()
        
    def create_session(self) -> requests.Session:
        """Create a requests session with proper headers."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        return session
    
    async def discover_all_courses_and_chapters(self) -> Dict[str, List[Tuple[str, str]]]:
        """Use Playwright to discover all courses and their chapters with navigation expansion."""
        logger.info("🎭 Phase 1: Discovering courses and chapters with Playwright...")
        
        course_chapters = {}
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Get all course links
                course_links = await self.find_all_course_links(page)
                logger.info(f"Found {len(course_links)} courses")
                
                # For each course, expand navigation and get all chapter links
                for i, (course_url, course_name) in enumerate(course_links, 1):
                    try:
                        logger.info(f"[{i}/{len(course_links)}] Discovering chapters for: {course_name}")
                        
                        chapters = await self.discover_chapters_for_course(page, course_url, course_name)
                        if chapters:
                            course_chapters[course_name] = chapters
                            logger.info(f"[{i}/{len(course_links)}] Found {len(chapters)} chapters")
                        else:
                            logger.warning(f"[{i}/{len(course_links)}] No chapters found")
                            
                    except Exception as e:
                        logger.error(f"[{i}/{len(course_links)}] Error discovering {course_name}: {e}")
                        continue
                        
            finally:
                await context.close()
                await browser.close()
                
        total_chapters = sum(len(chapters) for chapters in course_chapters.values())
        logger.info(f"✅ Phase 1 complete: {len(course_chapters)} courses, {total_chapters} chapters")
        
        return course_chapters
    
    async def find_all_course_links(self, page: Page) -> List[Tuple[str, str]]:
        """Find all course links from the main page."""
        await page.goto(self.base_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        course_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/docs/' in href and href.count('/') >= 4:  # Course links have specific structure
                full_url = urljoin(self.base_url, href)
                # Extract course name from URL
                parts = href.split('/')
                if len(parts) >= 3:
                    course_name = parts[2].replace('-', ' ')
                    course_links.append((full_url, course_name))
        
        # Remove duplicates by course name
        seen_courses = set()
        unique_courses = []
        for url, name in course_links:
            course_id = name.lower()
            if course_id not in seen_courses:
                unique_courses.append((url, name))
                seen_courses.add(course_id)
                
        return unique_courses
    
    async def discover_chapters_for_course(self, page: Page, course_url: str, course_name: str) -> List[Tuple[str, str]]:
        """Discover all chapters for a course using navigation expansion."""
        try:
            await page.goto(course_url, wait_until='domcontentloaded', timeout=15000)
            await page.wait_for_timeout(1000)
            
            # Expand navigation
            await self.expand_navigation(page)
            
            # Wait for expansion
            await page.wait_for_timeout(3000)
            
            # Get expanded content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all chapter links
            chapter_links = []
            course_identifier = self.extract_course_identifier(course_url)
            
            # Look in navigation
            nav_elem = soup.find('nav', class_='text-base lg:text-sm')
            if not nav_elem:
                nav_elem = soup.find('nav')
                
            if nav_elem:
                for link in nav_elem.find_all('a', href=True):
                    href = link['href']
                    if '/docs/' in href and course_identifier in href:
                        full_url = urljoin(self.base_url, href)
                        chapter_name = link.get_text(strip=True)
                        if chapter_name and full_url != course_url:
                            chapter_links.append((full_url, chapter_name))
            
            # Remove duplicates
            unique_chapters = []
            seen_urls = set()
            for url, name in chapter_links:
                if url not in seen_urls and name.strip():
                    unique_chapters.append((url, name))
                    seen_urls.add(url)
                    
            return unique_chapters
            
        except Exception as e:
            logger.error(f"Error discovering chapters for {course_name}: {e}")
            return []
    
    async def expand_navigation(self, page: Page) -> bool:
        """Expand all <li> sections in the navigation."""
        try:
            # Find navigation
            nav_selector = 'nav[class*="text-base"][class*="lg:text-sm"]'
            try:
                await page.wait_for_selector(nav_selector, timeout=5000)
            except:
                await page.wait_for_selector('nav', timeout=5000)
                nav_selector = 'nav'
            
            # Click all <li> elements
            li_elements = await page.query_selector_all(f'{nav_selector} li')
            expanded_count = 0
            
            for li_element in li_elements:
                try:
                    if await li_element.is_visible():
                        await li_element.click(timeout=1500)
                        expanded_count += 1
                        await page.wait_for_timeout(300)
                except Exception:
                    # Try clickable children
                    try:
                        clickable_children = await li_element.query_selector_all('button, div[role="button"], span[role="button"], a, .cursor-pointer')
                        for child in clickable_children:
                            try:
                                if await child.is_visible():
                                    await child.click(timeout=1500)
                                    expanded_count += 1
                                    await page.wait_for_timeout(300)
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue
            
            # Also try aria-expanded buttons
            try:
                expand_buttons = await page.query_selector_all('button[aria-expanded="false"]')
                for button in expand_buttons:
                    try:
                        if await button.is_visible():
                            await button.click(timeout=1000)
                            expanded_count += 1
                            await page.wait_for_timeout(300)
                    except Exception:
                        continue
            except Exception:
                pass
            
            await page.wait_for_timeout(2000)
            logger.debug(f"Navigation expansion completed - {expanded_count} elements clicked")
            return expanded_count > 0
            
        except Exception as e:
            logger.warning(f"Error expanding navigation: {e}")
            return False
    
    def extract_course_identifier(self, course_url: str) -> str:
        """Extract course identifier from URL."""
        try:
            parts = course_url.replace(self.base_url, '').split('/')
            if len(parts) >= 3:
                return parts[2]
        except:
            pass
        return ""
    
    def extract_chapter_content_http(self, session: requests.Session, chapter_url: str, chapter_name: str, course_name: str) -> Optional[Dict]:
        """Extract chapter content using HTTP request (fast)."""
        try:
            response = session.get(chapter_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article content
            article = soup.find('article')
            if not article:
                # Fallback to other content containers
                article = soup.find('main') or soup.find('.content') or soup.find('#content')
            
            if article:
                content = article.get_text(strip=True, separator=' ')
                if content:
                    return {
                        'course_name': course_name,
                        'chapter_name': chapter_name,
                        'chapter_url': chapter_url,
                        'content': content
                    }
                    
        except Exception as e:
            logger.warning(f"Error extracting {chapter_name}: {e}")
            
        return None
    
    def parallel_content_extraction(self, course_chapters: Dict[str, List[Tuple[str, str]]]) -> List[Dict]:
        """Extract content from all chapters in parallel using HTTP requests."""
        logger.info("⚡ Phase 2: Parallel content extraction with HTTP requests...")
        
        all_chapters = []
        for course_name, chapters in course_chapters.items():
            for chapter_url, chapter_name in chapters:
                all_chapters.append((course_name, chapter_url, chapter_name))
        
        logger.info(f"Extracting content from {len(all_chapters)} chapters using {self.max_workers} workers...")
        
        results = []
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Create a session for each worker
            sessions = {i: self.create_session() for i in range(self.max_workers)}
            
            # Submit all tasks
            future_to_chapter = {}
            for i, (course_name, chapter_url, chapter_name) in enumerate(all_chapters):
                session = sessions[i % self.max_workers]
                future = executor.submit(
                    self.extract_chapter_content_http,
                    session, chapter_url, chapter_name, course_name
                )
                future_to_chapter[future] = (course_name, chapter_name)
            
            # Collect results
            for future in as_completed(future_to_chapter):
                course_name, chapter_name = future_to_chapter[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                    completed += 1
                    
                    if completed % 50 == 0:
                        logger.info(f"Progress: {completed}/{len(all_chapters)} chapters ({completed/len(all_chapters)*100:.1f}%)")
                        
                except Exception as e:
                    logger.error(f"Error processing {chapter_name}: {e}")
                    completed += 1
        
        logger.info(f"✅ Phase 2 complete: {len(results)} chapters extracted")
        return results
    
    async def scrape_all_fast(self) -> List[Dict]:
        """Main method to scrape all content using the fast hybrid approach."""
        start_time = time.time()
        
        # Phase 1: Discovery with Playwright
        course_chapters = await self.discover_all_courses_and_chapters()
        
        phase1_time = time.time()
        logger.info(f"Phase 1 took {phase1_time - start_time:.2f} seconds")
        
        if not course_chapters:
            logger.error("No courses discovered")
            return []
        
        # Phase 2: Parallel content extraction with HTTP
        all_data = self.parallel_content_extraction(course_chapters)
        
        end_time = time.time()
        total_time = end_time - start_time
        phase2_time = end_time - phase1_time
        
        logger.info(f"Phase 2 took {phase2_time:.2f} seconds")
        logger.info(f"Total time: {total_time:.2f} seconds")
        logger.info(f"Average: {len(all_data)/total_time:.2f} chapters/second")
        
        return all_data
    
    def save_to_csv(self, data: List[Dict], filename: str = "kodekloud_content.csv"):
        """Save scraped data to CSV file."""
        if not data:
            logger.warning("No data to save")
            return
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['course_name', 'chapter_name', 'chapter_url', 'content']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            
            logger.info(f"Data saved to {filename} ({len(data)} rows)")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")

async def main():
    """Main function to run the scraper."""
    print("🚀 KodeKloud Content Scraper")
    print("=" * 50)
    print("🎭 Phase 1: Comprehensive course & chapter discovery")  
    print("⚡ Phase 2: Parallel content extraction")
    print(f"🔧 Using {16} parallel workers for maximum speed")
    print("=" * 50)
    
    scraper = KodeKloudScraper(max_workers=16, headless=True)
    
    try:
        start_time = time.time()
        
        # Run the fast scraping
        data = await scraper.scrape_all_fast()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if data:
            scraper.save_to_csv(data)
            
            print("\n" + "=" * 50)
            print("🎉 SUCCESS! Content scraping completed!")
            print(f"📚 Chapters scraped: {len(data)}")
            print(f"🎯 Unique courses: {len(set(row['course_name'] for row in data))}")
            print(f"⏱️  Total time: {duration:.2f} seconds")
            print(f"⚡ Speed: {len(data)/duration:.2f} chapters/second")
            print(f"📄 Data saved to: kodekloud_content.csv")
            print("🚀 High-performance hybrid scraping with comprehensive discovery!")
        else:
            print("❌ No data was scraped. Check the logs for errors.")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        print("\n⏹️  Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
