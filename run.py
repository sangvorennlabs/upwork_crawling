import argparse
from utils import *
from typing import List
from joblib import Parallel, delayed
import pandas

def main(search_query, openai_api_key):
    base_url = "https://www.upwork.com"

    clear_folder("cache")
    os.makedirs('cache', exist_ok=True)
    
    if openai_api_key:
        os.environ['OPENAI_API_KEY'] = openai_api_key
        print('OPENAI_API_KEY set succesfully')

    article_links = search_projects_upwork(search_query)

    results = crawl_4_ai_many([f"{base_url}{x}" for x in article_links])
    markdowns = [x.markdown for x in results]

    list_object:List[ResultStructure] = Parallel(n_jobs=-1, prefer="threads")(delayed(call_llm_services)(d) for d in markdowns)
    list_object = [x.model_dump() for x in list_object]

    df = pandas.DataFrame(list_object)
    df.to_csv("output.csv", index=False)

    print("Please check the file output.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search Upwork projects and process results.")
    parser.add_argument("-search_query", type=str, required=True, help="Search query for Upwork projects")
    parser.add_argument("-openai_api_key", type=str, required=False, help="OpenAI API key")
    
    args = parser.parse_args()
    
    main(args.search_query, args.openai_api_key)
