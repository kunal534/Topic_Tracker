import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from database_manager import DatabaseManager
from crawlers.reddit_crawler import RedditCrawler
from crawlers.youtube_crawler import YouTubeCrawler
from crawlers.google_crawler import GoogleCrawler
from summary_generator import SummaryGenerator
from content_processor import ContentProcessor

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, db_manager: DatabaseManager, crawlers: Dict, summary_generator: SummaryGenerator):
        self.db = db_manager
        self.reddit_crawler = crawlers['reddit']
        self.youtube_crawler = crawlers['youtube']
        self.google_crawler = crawlers['google']
        self.summary_generator = summary_generator
        self.content_processor = ContentProcessor()
        self.running = False
        self.scheduler_thread = None
    
    async def collect_content_for_task(self, task: Dict) -> Dict[str, List]:
        """Collect content from all sources for a task"""
        topic = task['topic']
        task_id = str(task['_id'])
        
        all_content = {
            'reddit': [],
            'youtube': [],
            'google': []
        }
        
        # Collect Reddit posts
        try:
            if self.reddit_crawler:
                reddit_posts = self.reddit_crawler.fetch_posts(topic, limit=30)
                if reddit_posts:
                    self.db.save_reddit_posts(task_id, reddit_posts)
                    all_content['reddit'] = reddit_posts
                    logger.info(f"Collected {len(reddit_posts)} Reddit posts for task {task_id}")
        except Exception as e:
            logger.error(f"Error collecting Reddit content for task {task_id}: {e}")
        
        # Collect YouTube videos
        try:
            if self.youtube_crawler:
                youtube_videos = self.youtube_crawler.fetch_videos(topic, max_results=20)
                if youtube_videos:
                    self.db.save_youtube_videos(task_id, youtube_videos)
                    all_content['youtube'] = youtube_videos
                    logger.info(f"Collected {len(youtube_videos)} YouTube videos for task {task_id}")
        except Exception as e:
            logger.error(f"Error collecting YouTube content for task {task_id}: {e}")
        
        # Collect Google search results
        try:
            if self.google_crawler:
                google_results = google_crawler.search(topic, num_results=25)
                if google_results:
                    self.db.save_google_results(task_id, google_results)
                    all_content['google'] = google_results
                    logger.info(f"Collected {len(google_results)} Google results for task {task_id}")
        except Exception as e:
            logger.error(f"Error collecting Google content for task {task_id}: {e}")
        
        return all_content
    
    async def process_single_task(self, task: Dict):
        """Process a single task"""
        task_id = str(task['_id'])
        topic = task['topic']
        
        try:
            logger.info(f"Processing task {task_id} for topic: {topic}")
            
            # Collect content from all sources
            content_dict = await self.collect_content_for_task(task)
            
            # Check if we have any content
            total_content = sum(len(content_list) for content_list in content_dict.values())
            if total_content == 0:
                logger.warning(f"No content collected for task {task_id}")
                # Still update the task to prevent it from running continuously
                self.db.update_task_run(task_id, task['interval_minutes'])
                return
            
            # Process content and generate summary
            try:
                processed_content, content_counts = self.content_processor.process_all_content(content_dict)
                
                if processed_content:
                    summary = self.summary_generator.generate_comprehensive_summary(processed_content, topic)
                    
                    # Save summary to database
                    self.db.save_summary(task_id, summary, content_counts)
                    
                    logger.info(f"Generated summary for task {task_id}. Content counts: {content_counts}")
                else:
                    logger.warning(f"No processable content for task {task_id}")
            
            except Exception as e:
                logger.error(f"Error generating summary for task {task_id}: {e}")
            
            # Update task's next run time
            self.db.update_task_run(task_id, task['interval_minutes'])
            
            logger.info(f"Completed processing task {task_id}")
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
    
    async def run_scheduled_tasks(self):
        """Run all tasks that are scheduled to run"""
        try:
            tasks_to_run = self.db.get_tasks_to_run()
            
            if not tasks_to_run:
                return
            
            logger.info(f"Found {len(tasks_to_run)} tasks to run")
            
            # Process tasks concurrently (but limit concurrency)
            semaphore = asyncio.Semaphore(3)  # Process max 3 tasks concurrently
            
            async def process_with_semaphore(task):
                async with semaphore:
                    await self.process_single_task(task)
            
            # Create tasks for concurrent processing
            task_coroutines = [process_with_semaphore(task) for task in tasks_to_run]
            
            # Wait for all tasks to complete
            await asyncio.gather(*task_coroutines, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in run_scheduled_tasks: {e}")
    
    def _scheduler_loop(self):
        """Main scheduler loop that runs in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("Task scheduler started")
        
        while self.running:
            try:
                # Run scheduled tasks
                loop.run_until_complete(self.run_scheduled_tasks())
                
                # Sleep for 60 seconds before checking again
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        loop.close()
        logger.info("Task scheduler stopped")
    
    def start(self):
        """Start the task scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Task scheduler thread started")
    
    def stop(self):
        """Stop the task scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("Stopping task scheduler...")
        self.running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Task scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get scheduler status"""
        return {
            'running': self.running,
            'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False,
            'active_tasks': len(self.db.get_active_tasks())
        }
    def is_running(self) -> bool:
        return getattr(self, "running", False)