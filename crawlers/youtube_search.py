import requests
from bs4 import BeautifulSoup
from typing import List

def search_youtube_video_ids(query: str, max_results: int = 10) -> List[str]:
    """
    Perform a simple search on YouTube and extract video IDs.
    This is a basic method using HTML parsing, may break if YouTube updates structure.
    """
    query = query.replace(' ', '+')
    url = f"https://www.youtube.com/results?search_query={query}"

    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        raise Exception(f"Failed to fetch YouTube search page. Status: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    video_ids = set()

    for link in soup.find_all('a'):
        href = link.get('href', '')
        if '/watch?v=' in href:
            video_id = href.split('=')[1].split('&')[0]
            video_ids.add(video_id)
        if len(video_ids) >= max_results:
            break

    return list(video_ids)

# Example usage:
if __name__ == "__main__":
    topic = "openai gpt-4"
    ids = search_youtube_video_ids(topic, max_results=5)
    print("Found video IDs:", ids)