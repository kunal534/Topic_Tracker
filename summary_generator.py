import requests
from typing import List, Dict, Optional
import logging
from content_processor import ContentProcessor
from config import Config  # ensure Config.RAPIDAPI_KEY_GPT is defined

logger = logging.getLogger(__name__)

class SummaryGenerator:
    def __init__(self, api_key: Optional[str] = None, model: str = "GPT-4.1-Mini"):
        self.api_key = api_key or Config.RAPIDAPI_KEY_GPT
        self.model = model
        self.processor = ContentProcessor(model)

    def _call_rapidapi_gpt(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            url = "https://chat-gpt26.p.rapidapi.com/"
            headers = {
                "Content-Type": "application/json",
                "x-rapidapi-host": "chat-gpt26.p.rapidapi.com",
                "x-rapidapi-key": self.api_key
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.error(f"RapidAPI GPT call failed: {e}")
            return f"Error generating summary: {str(e)}"

    def generate_batch_summary(self, content_batch: List[Dict], topic: str) -> str:
        try:
            content_texts = []
            for item in content_batch:
                source_label = item['source'].upper()
                content_texts.append(f"[{source_label}] {item['text']}")
            
            combined_content = "\n\n".join(content_texts)
            prompt = f"""Summarize the following content related to "{topic}". Focus on key points, trends, and important information:

{combined_content}

Provide a concise summary (3-4 sentences) highlighting the most relevant and recent developments."""
            
            return self._call_rapidapi_gpt(prompt, max_tokens=300)

        except Exception as e:
            logger.error(f"Error generating batch summary: {e}")
            return f"Error generating summary for this batch: {str(e)}"

    def generate_comprehensive_summary(self, all_content: List[Dict], topic: str) -> str:
        if not all_content:
            return "No content available to summarize."

        try:
            batches = self.processor.create_content_batches(all_content, 2500)

            if len(batches) == 1:
                return self.generate_batch_summary(batches[0], topic)

            batch_summaries = []
            for i, batch in enumerate(batches):
                summary = self.generate_batch_summary(batch, topic)
                batch_summaries.append(summary)
                logger.info(f"Generated summary for batch {i+1}/{len(batches)}")

            if not batch_summaries:
                return "Unable to generate summaries from the available content."

            combined_summaries = "\n\n".join([f"Section {i+1}: {s}" for i, s in enumerate(batch_summaries)])

            final_prompt = f"""Based on the following section summaries about "{topic}", create a comprehensive final summary:

{combined_summaries}

Provide a cohesive summary (4-6 sentences) that captures the main themes, trends, and important developments. Organize the information logically and highlight the most significant points."""

            return self._call_rapidapi_gpt(final_prompt, max_tokens=400)

        except Exception as e:
            logger.error(f"Error generating comprehensive summary: {e}")
            return f"Error generating comprehensive summary: {str(e)}"

    def generate_source_breakdown_summary(self, content_dict: Dict[str, List], topic: str) -> Dict[str, str]:
        summaries = {}

        for source, content_list in content_dict.items():
            if not content_list:
                summaries[source] = "No content available from this source."
                continue

            try:
                if source == 'reddit':
                    processed = self.processor.process_reddit_content(content_list, 2000)
                elif source == 'youtube':
                    processed = self.processor.process_youtube_content(content_list, 2000)
                elif source == 'google':
                    processed = self.processor.process_google_content(content_list, 2000)
                else:
                    continue

                if processed:
                    summaries[source] = self.generate_batch_summary(processed, topic)
                else:
                    summaries[source] = "No processable content from this source."

            except Exception as e:
                logger.error(f"Error generating {source} summary: {e}")
                summaries[source] = f"Error generating {source} summary: {str(e)}"

        return summaries