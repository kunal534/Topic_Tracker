import tiktoken
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class ContentProcessor:
    def __init__(self, model_name: str = "gpt-3.5-turbo", max_tokens: int = 4000):
        self.model_name = model_name
        self.max_tokens = max_tokens
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")  # fallback encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(str(text)))
    
    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit"""
        if not text:
            return ""
        
        tokens = self.encoding.encode(str(text))
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
    
    def process_reddit_content(self, posts: List[Dict], max_tokens: int = 3000) -> List[Dict]:
        """Process Reddit posts for summarization"""
        processed_posts = []
        current_tokens = 0
        
        # Sort by score (popularity) descending
        sorted_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)
        
        for post in sorted_posts:
            title = post.get('title', '')
            content = post.get('content', '')
            
            # Create content text
            post_text = f"Title: {title}\nContent: {content[:500]}"  # Limit content length
            post_tokens = self.count_tokens(post_text)
            
            if current_tokens + post_tokens > max_tokens:
                # Try to include a truncated version
                remaining_tokens = max_tokens - current_tokens - 50
                if remaining_tokens > 100:
                    truncated_text = self.truncate_text(post_text, remaining_tokens)
                    processed_posts.append({
                        'text': truncated_text,
                        'source': 'reddit',
                        'title': title,
                        'score': post.get('score', 0),
                        'truncated': True
                    })
                break
            
            processed_posts.append({
                'text': post_text,
                'source': 'reddit',
                'title': title,
                'score': post.get('score', 0),
                'truncated': False
            })
            current_tokens += post_tokens
        
        return processed_posts
    
    def process_youtube_content(self, videos: List[Dict], max_tokens: int = 3000) -> List[Dict]:
        """Process YouTube videos for summarization"""
        processed_videos = []
        current_tokens = 0
        
        # Sort by view count descending
        sorted_videos = sorted(videos, key=lambda x: x.get('view_count', 0), reverse=True)
        
        for video in sorted_videos:
            title = video.get('title', '')
            description = video.get('description', '')
            
            # Create content text
            video_text = f"Title: {title}\nDescription: {description[:400]}"  # Limit description
            video_tokens = self.count_tokens(video_text)
            
            if current_tokens + video_tokens > max_tokens:
                remaining_tokens = max_tokens - current_tokens - 50
                if remaining_tokens > 100:
                    truncated_text = self.truncate_text(video_text, remaining_tokens)
                    processed_videos.append({
                        'text': truncated_text,
                        'source': 'youtube',
                        'title': title,
                        'view_count': video.get('view_count', 0),
                        'truncated': True
                    })
                break
            
            processed_videos.append({
                'text': video_text,
                'source': 'youtube',
                'title': title,
                'view_count': video.get('view_count', 0),
                'truncated': False
            })
            current_tokens += video_tokens
        
        return processed_videos
    
    def process_google_content(self, results: List[Dict], max_tokens: int = 3000) -> List[Dict]:
        """Process Google search results for summarization"""
        processed_results = []
        current_tokens = 0
        
        for result in results:
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Create content text
            result_text = f"Title: {title}\nSnippet: {snippet}"
            result_tokens = self.count_tokens(result_text)
            
            if current_tokens + result_tokens > max_tokens:
                remaining_tokens = max_tokens - current_tokens - 50
                if remaining_tokens > 100:
                    truncated_text = self.truncate_text(result_text, remaining_tokens)
                    processed_results.append({
                        'text': truncated_text,
                        'source': 'google',
                        'title': title,
                        'truncated': True
                    })
                break
            
            processed_results.append({
                'text': result_text,
                'source': 'google',
                'title': title,
                'truncated': False
            })
            current_tokens += result_tokens
        
        return processed_results
    
    def create_content_batches(self, all_content: List[Dict], batch_size_tokens: int = 3000) -> List[List[Dict]]:
        """Split content into batches that fit within token limits"""
        batches = []
        current_batch = []
        current_tokens = 0
        
        for item in all_content:
            item_tokens = self.count_tokens(item['text'])
            
            if current_tokens + item_tokens > batch_size_tokens and current_batch:
                batches.append(current_batch)
                current_batch = [item]
                current_tokens = item_tokens
            else:
                current_batch.append(item)
                current_tokens += item_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def process_all_content(self, content_dict: Dict[str, List]) -> Tuple[List[Dict], Dict[str, int]]:
        """Process all content from different sources"""
        all_processed_content = []
        content_counts = {}
        
        # Process Reddit content
        if content_dict.get('reddit'):
            reddit_processed = self.process_reddit_content(content_dict['reddit'])
            all_processed_content.extend(reddit_processed)
            content_counts['reddit'] = len(content_dict['reddit'])
        else:
            content_counts['reddit'] = 0
        
        # Process YouTube content
        if content_dict.get('youtube'):
            youtube_processed = self.process_youtube_content(content_dict['youtube'])
            all_processed_content.extend(youtube_processed)
            content_counts['youtube'] = len(content_dict['youtube'])
        else:
            content_counts['youtube'] = 0
        
        # Process Google content
        if content_dict.get('google'):
            google_processed = self.process_google_content(content_dict['google'])
            all_processed_content.extend(google_processed)
            content_counts['google'] = len(content_dict['google'])
        else:
            content_counts['google'] = 0
        
        return all_processed_content, content_counts