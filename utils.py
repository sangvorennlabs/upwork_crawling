import requests
import asyncio
from crawl4ai import *
import re
from typing import List
from pydantic import BaseModel, Field
import openai
from joblib import Parallel, delayed
import pandas
import dotenv
dotenv.load_dotenv()

import os
import shutil

def clear_folder(folder_path):
    """
    Removes all files and subdirectories in the specified folder.

    Parameters:
    folder_path (str): The path to the folder to be cleared.
    """
    # Check if the folder exists
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Iterate over the files and directories in the given folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                # Remove files and symbolic links
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    print(f"Deleted file: {file_path}")
                # Remove directories
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"Deleted directory: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        print(f"The folder '{folder_path}' does not exist or is not a directory.")


def save(filename, content):
    with open(f"cache/{filename}", 'w', encoding='utf-8') as file:
        file.write(content)

def crawl_4_ai(url):
    async def crawl_4_ai_arun(url):
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            delay_before_return_html=2,  # 1 second delay before returning HTML content
        )
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                config=crawl_config,
                url=url,
            )
            save('search_result.html', result.html)
            return result
    
    return asyncio.run(crawl_4_ai_arun(url))

def crawl_4_ai_many(urls)-> List[CrawlResult]:
    async def crawl_batch(urls):
        final_result = []
        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=False,  # Default: get all results at once
            delay_before_return_html=1,
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            results = await crawler.arun_many(urls, config=run_config)
            for i, result in enumerate(results):
                print(f"URL: {result.url}, Success: {result.success}")
                save(f'project_result_{i}.html', result.html)
                final_result.append(result)
        
        return final_result
    
    return asyncio.run(crawl_batch(urls))

def crawl_4_ai_many(urls)-> List[CrawlResult]:
    result: List[ResultStructure] = Parallel(n_jobs=-1)(delayed(crawl_4_ai)(url) for url in urls)
    return result


def search_projects_upwork(query):
    crawled_result:CrawlResult = crawl_4_ai(f"https://www.upwork.com/services/search?q={query}")
    
    pattern = r'<a[^>]+href=[\'"]([^\'"]+)[\'"]'
    
    hrefs = re.findall(pattern, crawled_result.html)
    
    return [x for x in hrefs if "/services/product/" in x]

class ResultStructure(BaseModel):
    author_name:str = Field(description="The name of the author of that project")
    title:str 
    description:str = Field(description="The whole description of the project")
    hourly_rate:str
    prices_in_dollar: List[int] = Field(description="The list of prices in several tiers. There may be sometimes it has only one price")
    review_count: int
    overall_rating: float = Field(description="Overall rating from 0 to 5 stars")
    comments: List[str]
    author_location: str = Field(description="Location of the author")
    author_job_success_rate: float = Field(description="The percentage of job success from 0 to 100, from the author profile")
    author_bio: str = Field(description="A description about author")
    whats_included: str = Field(description="A markdown table for the section what included")
    
def call_llm_services(markdown):
    print("Begin: LLM extraction")
    client = openai.OpenAI(
        api_key = os.getenv("OPENAI_API_KEY")
    )
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
                {"role": "system", "content": "You are to extract a content from a website in markdown format to a predefine structure."},
                {"role": "user", "content": markdown},
            ],
            response_format=ResultStructure,
    )
    
    message:ResultStructure = completion.choices[0].message.parsed
    
    print("Done: LLM extraction")
    
    return message