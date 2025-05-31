"""
News aggregation module for Cascade News Analyzer.

This module handles collecting news from various sources including
social media, news sites, and RSS feeds.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import tweepy
from newsapi import NewsApiClient

from ..config import TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, NEWS_API_KEY

logger = logging.getLogger(__name__)


class TwitterCollector:
    """
    Collects tweets from Twitter using the Twitter API.
    """
    
    def __init__(self):
        """
        Initialize the Twitter collector with API credentials.
        """
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self) -> None:
        """
        Initialize the Twitter client with credentials.
        """
        try:
            auth = tweepy.OAuth1UserHandler(
                TWITTER_API_KEY, 
                TWITTER_API_SECRET,
                TWITTER_ACCESS_TOKEN, 
                TWITTER_ACCESS_SECRET
            )
            self.client = tweepy.API(auth)
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            self.client = None
    
    def collect_tweets(self, query: str, count: int = 100) -> List[Dict[str, Any]]:
        """
        Collect tweets based on a search query.
        
        Args:
            query (str): Search query
            count (int, optional): Number of tweets to collect. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of collected tweets
        """
        if not self.client:
            logger.error("Twitter client not initialized")
            return []
        
        try:
            tweets = self.client.search_tweets(q=query, count=count, tweet_mode='extended')
            logger.info(f"Collected {len(tweets)} tweets for query: {query}")
            
            result = []
            for tweet in tweets:
                result.append({
                    'id': tweet.id_str,
                    'text': tweet.full_text,
                    'user': tweet.user.screen_name,
                    'created_at': tweet.created_at.isoformat(),
                    'retweet_count': tweet.retweet_count,
                    'favorite_count': tweet.favorite_count,
                    'source': 'twitter'
                })
            return result
        except Exception as e:
            logger.error(f"Error collecting tweets: {str(e)}")
            return []


class NewsAPICollector:
    """
    Collects news articles from NewsAPI.
    """
    
    def __init__(self):
        """
        Initialize the NewsAPI collector with API key.
        """
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self) -> None:
        """
        Initialize the NewsAPI client with credentials.
        """
        try:
            self.client = NewsApiClient(api_key=NEWS_API_KEY)
            logger.info("NewsAPI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize NewsAPI client: {str(e)}")
            self.client = None
    
    def collect_articles(self, query: str, sources: Optional[str] = None, 
                         from_date: Optional[str] = None, to_date: Optional[str] = None, 
                         language: str = 'en', sort_by: str = 'publishedAt',
                         page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Collect news articles based on a search query.
        
        Args:
            query (str): Search query
            sources (Optional[str], optional): Comma-separated news sources. Defaults to None.
            from_date (Optional[str], optional): Start date in YYYY-MM-DD format. Defaults to None.
            to_date (Optional[str], optional): End date in YYYY-MM-DD format. Defaults to None.
            language (str, optional): Language code. Defaults to 'en'.
            sort_by (str, optional): Sort order. Defaults to 'publishedAt'.
            page_size (int, optional): Number of articles per page. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of collected articles
        """
        if not self.client:
            logger.error("NewsAPI client not initialized")
            return []
        
        try:
            articles = self.client.get_everything(
                q=query,
                sources=sources,
                from_param=from_date,
                to=to_date,
                language=language,
                sort_by=sort_by,
                page_size=page_size
            )
            
            logger.info(f"Collected {len(articles.get('articles', []))} articles for query: {query}")
            
            result = []
            for article in articles.get('articles', []):
                result.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'unknown'),
                    'author': article.get('author', ''),
                    'published_at': article.get('publishedAt', ''),
                    'source_type': 'newsapi'
                })
            return result
        except Exception as e:
            logger.error(f"Error collecting articles: {str(e)}")
            return []


class NewsAggregator:
    """
    Aggregates news from multiple sources.
    """
    
    def __init__(self):
        """
        Initialize the news aggregator with collectors.
        """
        self.twitter_collector = TwitterCollector()
        self.news_api_collector = NewsAPICollector()
    
    def collect_news(self, query: str, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Collect news from multiple sources based on a query.
        
        Args:
            query (str): Search query
            sources (Optional[List[str]], optional): List of sources to collect from. Defaults to None.
            
        Returns:
            List[Dict[str, Any]]: Aggregated news items
        """
        if sources is None:
            sources = ['twitter', 'newsapi']
        
        results = []
        
        if 'twitter' in sources:
            tweets = self.twitter_collector.collect_tweets(query)
            results.extend(tweets)
            
        if 'newsapi' in sources:
            articles = self.news_api_collector.collect_articles(query)
            results.extend(articles)
        
        # Sort by date (most recent first)
        results.sort(key=lambda x: x.get('published_at', x.get('created_at', '')), reverse=True)
        
        logger.info(f"Aggregated {len(results)} news items for query: {query}")
        
        return results

