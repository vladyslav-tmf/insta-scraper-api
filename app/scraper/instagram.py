import logging
from datetime import datetime

from selenium import webdriver
from selenium.common import (
    WebDriverException,
    SessionNotCreatedException,
    TimeoutException,
    NoSuchElementException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from app.core.config import Settings
from app.models.instagram import InstagramPost

logger = logging.getLogger(__name__)


class InstagramScraper:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.driver = None
        self.is_initialized = False

    def initialize(self) -> None:
        """Initialize the Selenium webdriver."""
        if self.is_initialized:
            return

        try:
            chrome_options = Options()

            if self.settings.HEADLESS_BROWSER:
                chrome_options.add_argument("--headless")

            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            )

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(self.settings.BROWSER_TIMEOUT)
            self.is_initialized = True

            logger.info("Selenium WebDriver initialized successfully")

        except (WebDriverException, SessionNotCreatedException) as error:
            logger.error(f"Failed to initialize Selenium WebDriver: {error}")
            raise

    def close(self) -> None:
        """Close the Selenium webdriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_initialized = False
            logger.info("Selenium WebDriver closed")

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @staticmethod
    def extract_post_id(shortcode: str) -> str:
        """Extract Instagram post ID from shortcode."""
        return f"post_{shortcode}"

    @staticmethod
    def extract_hashtags(text: str) -> list[str]:
        """Extract hashtags from post text."""
        if not text:
            return []

        words = text.split()
        return [word for word in words if word.startswith("#") and len(word) > 1]

    @staticmethod
    def contains_target_hashtag(hashtags: list[str], target_hashtag: str) -> bool:
        """Check if post contains the target hashtag."""
        if not target_hashtag.startswith("#"):
            target_hashtag = f"#{target_hashtag}"

        return target_hashtag.lower() in [hashtag.lower() for hashtag in hashtags]

    def scrape_account(
        self, account_name: str, limit: int = 10, target_hashtag: str = "#Space"
    ) -> list[InstagramPost]:
        """Scrape Instagram posts from specified account."""
        posts: list[InstagramPost] = []
        account_url = f"https://www.instagram.com/{account_name}"

        with self:
            try:
                logger.info(f"Navigating to Instagram account: {account_url}")
                self.driver.get(account_url)

                try:
                    WebDriverWait(self.driver, self.settings.BROWSER_TIMEOUT).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article a"))
                    )
                except (TimeoutException, NoSuchElementException):
                    logger.warning(
                        f"Timeout waiting for posts to load on {account_url}"
                    )

                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "article a")
                post_links = [
                    element.get_attribute("href")
                    for element in post_elements
                    if "/p/" in element.get_attribute("href")
                ]
                post_links = post_links[:limit]

                logger.info(f"Found {len(post_links)} posts to scrape")

                for post_link in post_links:
                    try:
                        post = self.scrape_post(post_link, target_hashtag)

                        if post:
                            posts.append(post)

                    except (
                        NoSuchElementException,
                        TimeoutException,
                        WebDriverException,
                    ) as error:
                        logger.error(f"Error scraping post {post_link}: {error}")
                        continue

                logger.info(f"Successfully scraped {len(posts)} posts")
                return posts

            except (WebDriverException, TimeoutException) as error:
                logger.error(f"Error scraping account {account_name}: {error}")
                return posts

    def scrape_post(self, post_url: str, target_hashtag: str) -> InstagramPost | None:
        """Scrape a single Instagram post."""
        try:
            logger.info(f"Scraping post: {post_url}")
            self.driver.get(post_url)

            try:
                WebDriverWait(self.driver, self.settings.BROWSER_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
                )
            except (TimeoutException, NoSuchElementException):
                logger.warning(f"Timeout waiting for post to load on {post_url}")
            shortcode = post_url.split("/p/")[1].rstrip("/")

            try:
                caption_element = WebDriverWait(
                    self.driver, self.settings.BROWSER_TIMEOUT
                ).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div._a9zs")))
                caption = caption_element.text
            except (TimeoutException, NoSuchElementException):
                caption = ""

            try:
                likes_element = self.driver.find_element(
                    By.CSS_SELECTOR, "section._ae5m span"
                )
                likes_text = likes_element.text
                likes_count = int(
                    "".join(char for char in likes_text if char.isdigit())
                )
            except (NoSuchElementException, ValueError):
                likes_count = 0

            try:
                comments_count = len(
                    self.driver.find_elements(By.CSS_SELECTOR, "ul._a9ym li")
                )
            except NoSuchElementException:
                comments_count = 0

            try:
                image_element = self.driver.find_element(By.CSS_SELECTOR, "img._aagt")
                image_url = image_element.get_attribute("src")
            except NoSuchElementException:
                image_url = None

            timestamp = None
            try:
                time_element = self.driver.find_element(By.CSS_SELECTOR, "time._aaqe")
                datetime_str = time_element.get_attribute("datetime")

                if datetime_str:
                    timestamp = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
            except (NoSuchElementException, ValueError) as error:
                logger.warning(f"Failed to extract timestamp from post: {error}")

            hashtags = self.extract_hashtags(caption)
            has_target_hashtag = self.contains_target_hashtag(hashtags, target_hashtag)

            post = InstagramPost(
                post_id=self.extract_post_id(shortcode),
                shortcode=shortcode,
                url=post_url,
                caption=caption,
                likes_count=likes_count,
                comments_count=comments_count,
                image_url=image_url,
                hashtags=hashtags,
                contains_target_hashtag=has_target_hashtag,
                timestamp=timestamp,
            )

            logger.info(f"Successfully scraped post {shortcode}")
            return post

        except (
            NoSuchElementException,
            TimeoutException,
            WebDriverException,
            ValueError,
        ) as error:
            logger.error(f"Error scraping post {post_url}: {error}")
            return None
