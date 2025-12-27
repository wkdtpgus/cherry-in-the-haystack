import os
import time
import requests
from datetime import datetime
from typing import List, Dict

from ops_base import OperatorBase
from config.api_sources import (
    HACKERNEWS_API,
    DEVTO_API,
    KEYWORDS_CONFIG
)
import utils
import llm_prompts
from llm_agent import LLMAgentSummary
import re
from db_cli import DBClient


class OperatorAPICrawler(OperatorBase):
    def __init__(self):
        super().__init__()
        self.client = DBClient()

    def pull(self):
        """
        Pull articles from API sources (HackerNews, Dev.to)
        """
        print("######################################################")
        print("# Pulling from API Crawler Sources")
        print("######################################################")
        
        all_articles = []
        
        # 1. Hacker News
        hn_articles = self._pull_hackernews(limit=5)
        all_articles.extend(hn_articles)
        
        # 2. Dev.to
        devto_articles = self._pull_devto(limit=3)
        all_articles.extend(devto_articles)
        
        # Global limit 10
        all_articles = all_articles[:10]
        
        print(f"Total pulled from API sources: {len(all_articles)}")
        return all_articles

    def _pull_hackernews(self, limit=30) -> List[Dict]:
        print(f"[{self.__class__.__name__}] Pulling from HackerNews...")
        articles = []
        keywords = KEYWORDS_CONFIG["HackerNews"]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            # Get top stories IDs
            resp = requests.get(f"{HACKERNEWS_API}/topstories.json", headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"[ERROR] Failed to fetch HN top stories: {resp.status_code}")
                return []
                
            story_ids = resp.json()[:limit] # Check more if needed, but start small
            
            for sid in story_ids:
                try:
                    item_resp = requests.get(f"{HACKERNEWS_API}/item/{sid}.json", headers=headers, timeout=5)
                    if item_resp.status_code != 200:
                        continue
                        
                    item = item_resp.json()
                    if not item or item.get("type") != "story":
                        continue
                        
                    title = item.get("title", "")
                    text = item.get("text", "")
                    url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                    
                    # Keyword filtering
                    content_to_check = f"{title} {text}".lower()
                    if any(k.lower() in content_to_check for k in keywords):
                        articles.append({
                            "id": utils.hashcode_md5(f"HN_{sid}".encode('utf-8')),
                            "source": "HackerNews",
                            "list_name": "HackerNews (AI)",
                            "title": title,
                            "url": url,
                            "created_time": datetime.fromtimestamp(item.get("time", time.time())).isoformat(),
                            "summary": text[:500] if text else "",
                            "content": text,
                            "tags": [],
                            "score": item.get("score", 0),
                            "published_key": datetime.fromtimestamp(item.get("time", time.time())).strftime("%Y-%m-%d")
                        })
                        print(f"  -> Found relevant HW item: {title}")
                        
                except Exception as e:
                    print(f"[WARN] Failed to fetch HN item {sid}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[ERROR] HackerNews pull failed: {e}")
            
        return articles

    def _pull_devto(self, limit=20) -> List[Dict]:
        print(f"[{self.__class__.__name__}] Pulling from Dev.to...")
        articles = []
        tags = KEYWORDS_CONFIG["DevTo"]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/vnd.forem.api-v1+json'
        }
        
        for tag in tags:
            try:
                params = {"tag": tag, "per_page": limit}
                resp = requests.get(DEVTO_API, params=params, headers=headers, timeout=10)
                
                if resp.status_code != 200:
                    print(f"[ERROR] Dev.to tag {tag} failed: {resp.status_code}")
                    continue
                    
                items = resp.json()
                for item in items:
                    # Dev.to usually returns relevant items given the tag
                    articles.append({
                        "id": utils.hashcode_md5(f"DevTo_{item.get('id')}".encode('utf-8')),
                        "source": "Dev.to",
                        "list_name": f"Dev.to ({tag})",
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "created_time": item.get("published_at", datetime.now().isoformat()),
                        "summary": item.get("description", ""),
                        "content": item.get("body_markdown", ""), # Dev.to returns markdown body
                        "tags": item.get("tag_list", []),
                        "score": item.get("positive_reactions_count", 0),
                        "published_key": item.get("published_at", datetime.now().isoformat())[:10]
                    })
                
                print(f"  -> Found {len(items)} items for tag #{tag}")
                time.sleep(1) 
                
            except Exception as e:
                print(f"[ERROR] Dev.to tag {tag} failed: {e}")
                
        return articles

    def _init_llm_agent(self):
        agent = LLMAgentSummary()
        return agent

    def summarize(self, pages):
        """
        Summarize the fetched pages using LLM
        """
        print("######################################################")
        print("# Summarize API Crawler Articles")
        print("######################################################")

        llm_agent = self._init_llm_agent()
        
        # Use generic prompt
        prompt_tpl = llm_prompts.LLM_PROMPT_API_SUMMARY
        llm_agent.init_prompt(combine_prompt=prompt_tpl)
        llm_agent.init_llm()

        for page in pages:
            title = page["title"]
            url = page["url"]
            source = page.get("source", "API")
            page_id = page["id"]
            
            print(f"Summarying page, title: {title}, source: {source}")

            # cache check
            summary = self.client.get_notion_summary_item_id(
                "api_crawl", source, page_id) # Use "api_crawl" as source key for cache logic consistency? Or just source.

            # Force update for prompt change
            summary = None 
            if summary:
                print(f"Cache hit for summary: {title}")
                page["summary"] = utils.bytes2str(summary)
                continue

            # Load content
            content = page.get("content", "")
            if not content:
                content = utils.load_web(url)
            
            if not content:
                print("Web load failed, using description as fallback")
                content = page.get("summary", "") # Use the short summary from API

            if not content:
                print("No content to summarize")
                continue

            # Run LLM
            try:
                summary = llm_agent.run(content)
                
                # Save cache (reuse RSS summary cache key structure)
                self.client.set_notion_summary_item_id(
                    "api_crawl", source, page_id, summary,
                    expired_time=60*60*24*7) # 7 days
                
                page["summary"] = summary
                
            except Exception as e:
                print(f"[ERROR] LLM Summary failed: {e}")

        return pages

    def dedup(self, extractedPages, target="inbox"):
        print("#####################################################")
        print("# Dedup API Crawler Pages")
        print("#####################################################")
        client = DBClient()
        deduped_pages = []
        
        # extractedPages can be list (from current pull) or dict (if structure changes)
        if isinstance(extractedPages, dict):
            iterator = extractedPages.values()
        else:
            iterator = extractedPages

        for page in iterator:
            page_id = page["id"]
            title = page["title"]
            source = page.get("source", "API")
            list_name = page.get("list_name", "API")
            
            # Use 'api_crawl' as source key for dedup check to match summary cache
            is_dup = client.get_notion_toread_item_id("api_crawl", list_name, page_id)
            
            # FORCE INCLUDE DUP for testing new summary
            print(f" - Duplicate check: {is_dup} (Forcing inclusion)")
            deduped_pages.append(page)
            
            # if not client.get_notion_toread_item_id("api_crawl", list_name, page_id):
            #     deduped_pages.append(page)
            # else:
            #      print(f" - Duplicate found, skipping: {title}")
                 
        print(f"Deduped pages count: {len(deduped_pages)}")
        return deduped_pages

    def score(self, data, **kwargs):
        # Pass-through for now
        return data

    def rank(self, data, **kwargs):
        # Pass-through for now
        return data

    def _parse_summary(self, page):
        """
        Parse Markdown summary into structural fields:
        __summary, __why_it_matters, __examples, __insights
        """
        raw_summary = page.get("summary", "")
        if not raw_summary:
            return

        # Initialize defaults
        page["__summary"] = ""
        page["__why_it_matters"] = ""
        page["__examples"] = []
        page["__insights"] = []

        # Regex patterns for headers
        patterns = {
            "ai_summary": r"##\s*💡\s*AI\s*요약.*?\(AI\s*Summary\)\s*(.*?)(?=##|$)",
            "why_it_matters": r"##\s*❓\s*왜\s*중요한가.*?\(Why\s*it\s*matters\)\s*(.*?)(?=##|$)",
            "examples": r"##\s*🔍\s*예시.*?\(Example\)\s*(.*?)(?=##|$)",
            "insights": r"##\s*⚡\s*인사이트.*?\(Insight\)\s*(.*?)(?=##|$)"
        }

        # Parsing
        for key, pattern in patterns.items():
            match = re.search(pattern, raw_summary, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                
                if key == "ai_summary":
                    page["__summary"] = content
                elif key == "why_it_matters":
                    page["__why_it_matters"] = content
                elif key in ["examples", "insights"]:
                    # Convert bullet points to list
                    items = [
                        line.strip().lstrip("-").lstrip("•").strip() 
                        for line in content.split('\n') 
                        if line.strip().startswith("-") or line.strip().startswith("•")
                    ]
                    # If no bullet points found, just take the whole text as one item (or fallback)
                    if not items and content:
                        items = [content]
                        
                    page[f"__{key}"] = items

        # Fallback: if parsing failed entirely (no headers), put everything in __summary
        if not page["__summary"] and not page["__why_it_matters"]:
            page["__summary"] = raw_summary

    def push(self, pages, targets, topk=3):
        print("#####################################################")
        print("# Push API Crawler Data")
        print("#####################################################")
        
        from notion import NotionAgent
        from ops_notion import OperatorNotion
        import traceback

        stat = {"total": 0, "error": 0}

        for target in targets:
            print(f"Pushing data to target: {target} ...")

            if target == "notion":
                notion_api_key = os.getenv("NOTION_TOKEN")
                notion_agent = NotionAgent(notion_api_key)
                
                database_id = os.getenv("NOTION_ENTRY_PAGE_ID", "2a6f199edf7c809eac47c77106b34c38")
                print(f"Target Database ID: {database_id}")

                for page in pages:
                    stat["total"] += 1
                    try:
                        # Parse structured summary
                        self._parse_summary(page)
                        
                        page_id = page["id"]
                        list_name = page.get("list_name", "API")
                        title = page["title"]
                        
                        print(f"Pushing page: {title}")
                        
                        # Simplified topics/categories
                        tags = page.get("tags", [])
                        topics_topk = [str(t) for t in tags][:3]
                        categories_topk = []

                        # Reuse RSS item creation as it fits the schema mostly
                        notion_agent.createDatabaseItem_ToRead_RSS(
                            database_id,
                            page,
                            topics_topk,
                            categories_topk
                        )
                        
                        # Mark as visited
                        self.client.set_notion_toread_item_id("api_crawl", list_name, page_id)

                    except Exception as e:
                        print(f"[ERROR] Push failed for {title}: {e}")
                        stat["error"] += 1
                        traceback.print_exc()
                        
        return stat
