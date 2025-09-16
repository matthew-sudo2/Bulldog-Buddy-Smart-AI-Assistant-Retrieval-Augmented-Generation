"""
Web content scraper for Bulldog Buddy - extracts content from URLs for analysis
"""

import requests
from bs4 import BeautifulSoup
import validators
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, List, Optional
import logging
import time

class WebContentScraper:
    """Web content scraper that can extract text content from websites"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            return validators.url(url)
        except:
            return False
    
    def clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def scrape_website(self, url: str) -> Dict[str, any]:
        """
        Scrape website content using BeautifulSoup
        Returns: Dict with title, content, url, method_used
        """
        url = self.clean_url(url)
        
        if not self.is_valid_url(url):
            return {"error": "Invalid URL format"}
        
        try:
            # Try newspaper3k first (if available)
            try:
                from newspaper import Article
                article = Article(url)
                article.download()
                article.parse()
                
                if article.text and len(article.text) > 100:
                    return {
                        "title": article.title or "Web Page",
                        "content": article.text,
                        "url": url,
                        "method": "newspaper3k",
                        "word_count": len(article.text.split()),
                        "publish_date": str(article.publish_date) if article.publish_date else None
                    }
            except ImportError:
                logging.info("Newspaper3k not available, using BeautifulSoup")
            except Exception as e:
                logging.warning(f"Newspaper3k failed for {url}: {e}")
            
            # Fallback to BeautifulSoup
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'iframe', 'noscript']):
                element.decompose()
            
            # Extract title
            title = soup.find('title')
            title = title.get_text().strip() if title else "Web Page"
            
            # Extract main content - try multiple strategies
            content_text = ""
            
            # Strategy 1: Look for main content containers
            content_selectors = [
                'article', 'main', '[role="main"]', '.content', '.main-content',
                '.post-content', '.entry-content', '.article-content', '.page-content'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text().strip()
                    if len(text) > 200:  # Only include substantial content
                        content_text += text + "\n\n"
                        break
                if content_text:
                    break
            
            # Strategy 2: If no main content found, get all paragraphs
            if not content_text:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 50:  # Only meaningful paragraphs
                        content_text += text + "\n\n"
            
            # Strategy 3: If still no content, get all text
            if not content_text:
                content_text = soup.get_text()
            
            # Clean up content
            content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = content_text.strip()
            
            if len(content_text) > 100:
                return {
                    "title": title,
                    "content": content_text,
                    "url": url,
                    "method": "beautifulsoup",
                    "word_count": len(content_text.split())
                }
            else:
                return {"error": "Could not extract sufficient content from the webpage"}
                
        except requests.exceptions.Timeout:
            return {"error": "Website took too long to respond"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to access website: {str(e)}"}
        except Exception as e:
            return {"error": f"Error processing website: {str(e)}"}
    
    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple URLs with rate limiting"""
        results = []
        for url in urls:
            result = self.scrape_website(url)
            results.append(result)
            time.sleep(1)  # Be respectful to servers
        return results
