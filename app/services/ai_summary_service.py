"""
AI Summary Service for Quest
Generates intelligent summaries of user insights using ChatGPT API
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.database import get_supabase_service

logger = logging.getLogger(__name__)

class AISummaryService:
    """AI-powered summary service for insights analysis"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.chat_model = os.getenv('CHAT_MODEL', 'gpt-4o-mini')
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenAI client following the embedding service pattern"""
        try:
            import openai
        except ImportError:
            logger.warning("OpenAI library not available, AI summary will be disabled")
            return
        
        if not self.openai_api_key:
            logger.warning("OpenAI API Key not configured, AI summary will be disabled")
            return
        
        try:
            self.client = openai.AsyncOpenAI(
                api_key=self.openai_api_key,
                base_url=self.openai_base_url,
                timeout=30.0
            )
            logger.info(f"OpenAI AI Summary client initialized successfully, model: {self.chat_model}")
        except Exception as e:
            logger.error(f"OpenAI client initialization failed: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if AI summary service is available"""
        return self.client is not None and self.openai_api_key is not None
    
    async def _health_check(self) -> tuple[bool, str]:
        """Test if the OpenAI client can actually make API calls"""
        if not self.is_available():
            return False, "Client not available / missing key"
        try:
            # Very cheap request
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": "Return the word OK"}],
                max_tokens=5,
                temperature=0
            )
            content = response.choices[0].message.content if response.choices else "No content"
            return True, f"OK - Response: {content}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
        
    async def generate_weekly_insights_summary(self, user_id: str) -> str:
        """
        Generate AI summary of user's insights from the past week
        
        Args:
            user_id: User ID to get insights for
            
        Returns:
            AI-generated summary with up to 5 key bullet points
        """
        try:
            if not self.is_available():
                logger.warning("AI summary service not available, returning fallback summary")
                return self._get_fallback_summary(user_id)
            
            # Get insights from the past week
            insights = await self._get_weekly_insights(user_id)
            
            if not insights:
                return "No new insights captured this week. Consider adding some content to build your knowledge base!"
            
            # Generate AI summary
            summary = await self._generate_ai_summary(insights)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._get_fallback_summary(user_id)
    
    async def _get_weekly_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get insights from the past week for a user
        Uses the same pattern as digest_repo.py for consistency
        
        Args:
            user_id: User ID
            
        Returns:
            List of insight objects with summaries
        """
        try:
            from datetime import timezone
            
            # Calculate date range (past 7 days) - match digest_repo.py pattern
            now_utc = datetime.now(timezone.utc)
            start_utc = now_utc - timedelta(days=7)
            
            logger.info(f"AI SUMMARY: Fetching insights for user {user_id} from {start_utc.isoformat()} to {now_utc.isoformat()}")
            
            # Use the same query pattern as digest_repo.py for consistency
            query = self.supabase.table("insights").select(
                """
                id,
                title,
                description,
                url,
                image_url,
                created_at,
                updated_at,
                tags,
                stack_id,
                insight_contents(
                    summary,
                    thought
                )
                """
            ).eq("user_id", user_id).order("created_at", desc=True)
            
            # Execute query
            resp = query.execute()
            if hasattr(resp, "error") and resp.error:
                logger.error(f"AI SUMMARY: Error fetching insights for user {user_id}: {resp.error}")
                return []
            
            rows = resp.data or []
            logger.info(f"AI SUMMARY: Retrieved {len(rows)} total insights for user {user_id}")
            
            # Filter in Python: include items created OR updated within window (same as digest_repo.py)
            def _parse_dt(s: str) -> datetime:
                # Handle "Z" and timezone-aware strings robustly
                if not s:
                    return None
                try:
                    # Normalize trailing 'Z'
                    if s.endswith("Z"):
                        s = s[:-1] + "+00:00"
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            
            recent = []
            for it in rows:
                c = _parse_dt(it.get("created_at"))
                u = _parse_dt(it.get("updated_at"))
                # Use created_at primarily, fall back to updated_at; count either if within window
                in_window = False
                if c and c >= start_utc:
                    in_window = True
                elif u and u >= start_utc:
                    in_window = True
                if in_window:
                    recent.append(it)
            
            logger.info(f"AI SUMMARY: Found {len(recent)} insights for user {user_id} in last 7 days")
            return recent
                
        except Exception as e:
            logger.error(f"Error fetching weekly insights: {e}")
            return []
    
    async def _generate_ai_summary(self, insights: List[Dict[str, Any]]) -> str:
        """
        Generate AI summary using ChatGPT API
        
        Args:
            insights: List of insight objects
            
        Returns:
            AI-generated summary with key bullet points
        """
        try:
            # Prepare insights data for AI analysis
            insights_text = self._format_insights_for_ai(insights)
            
            logger.info(f"AI SUMMARY DEBUG: Formatted insights text length: {len(insights_text)}")
            logger.info(f"AI SUMMARY DEBUG: First 200 chars of insights: {insights_text[:200]}...")
            
            if not insights_text.strip():
                return "No meaningful content found in this week's insights."
            
            # Create AI prompt for correlation analysis
            prompt = self._create_summary_prompt(insights_text, len(insights))
            
            logger.info(f"AI SUMMARY DEBUG: Prompt length: {len(prompt)}")
            logger.info(f"AI SUMMARY DEBUG: Model: {self.chat_model}, Base URL: {self.openai_base_url}")
            
            # Call ChatGPT API
            summary = await self._call_chatgpt_api(prompt)
            
            if summary:
                logger.info("AI summary generated successfully")
                logger.info(f"AI SUMMARY DEBUG: Generated summary length: {len(summary)}")
                logger.info(f"AI SUMMARY DEBUG: Generated summary preview: {summary[:200]}...")
                return summary
            else:
                logger.warning("AI summary generation failed, using fallback")
                return self._get_fallback_summary_from_insights(insights)
                
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            import traceback
            logger.error(f"AI summary generation traceback: {traceback.format_exc()}")
            return self._get_fallback_summary_from_insights(insights)
    
    def _format_insights_for_ai(self, insights: List[Dict[str, Any]]) -> str:
        """
        Format insights data for AI analysis
        Handles the insight_contents join structure from digest_repo.py
        
        Args:
            insights: List of insight objects with insight_contents join
            
        Returns:
            Formatted text for AI processing
        """
        formatted_insights = []
        
        for i, insight in enumerate(insights, 1):
            # Extract content from insight_contents join structure
            content = ""
            insight_contents = insight.get('insight_contents', [])
            
            if insight_contents and len(insight_contents) > 0:
                # Use summary from insight_contents if available
                content = insight_contents[0].get('summary', '') or insight_contents[0].get('thought', '')
            
            # Fall back to description if no insight_contents summary
            if not content.strip():
                content = insight.get('description', '')
            
            title = insight.get('title', f'Insight {i}')
            url = insight.get('url', '')
            tags = insight.get('tags', [])
            
            if not content.strip():
                continue
                
            insight_text = f"**{title}**"
            if url:
                insight_text += f" ({url})"
            if tags:
                # Handle tags as list of dictionaries with 'name' field
                if isinstance(tags, list) and len(tags) > 0:
                    if isinstance(tags[0], dict):
                        # Tags are dictionaries with 'name' field
                        tag_names = [tag.get('name', '') for tag in tags if isinstance(tag, dict) and tag.get('name')]
                        insight_text += f" [Tags: {', '.join(tag_names)}]"
                    else:
                        # Tags are strings
                        insight_text += f" [Tags: {', '.join(tags)}]"
                else:
                    # Single tag or other format
                    insight_text += f" [Tags: {tags}]"
            insight_text += f"\n{content.strip()}\n"
            
            formatted_insights.append(insight_text)
        
        return "\n".join(formatted_insights)
    
    def _create_summary_prompt(self, insights_text: str, insight_count: int) -> str:
        """
        Create prompt for ChatGPT to analyze insights and find correlations
        
        Args:
            insights_text: Formatted insights text
            insight_count: Number of insights
            
        Returns:
            ChatGPT prompt
        """
        return f"""你是一个AI助手，用于分析个人知识洞察，识别模式、关联和关键主题。

分析以下本周捕获的{insight_count}个洞察，并提供最多3个关键要点的总结：

1. 识别洞察中的共同主题或模式
2. 突出不同信息片段之间有趣的关联或联系
3. 提取最有价值或可操作的洞察

专注于寻找有意义的连接和模式，而不是仅仅列出个人洞察。

要分析的洞察：
{insights_text}

请提供你的分析，作为3个简洁的要点，每个以•符号开头。每个要点应该是一句话，专注于你识别出的最重要的模式、关联或洞察。

重要：请用中文回复，格式如下，每个要点占一行：

• [关键洞察或模式1]
• [关键洞察或模式2]  
• [关键洞察或模式3]

如果发现少于3个不同的模式，请提供你能识别的最重要的模式。确保每个要点都在单独的一行上，并且每个要点只占一行。"""
    
    async def _call_chatgpt_api(self, prompt: str) -> Optional[str]:
        """
        Call ChatGPT API to generate summary using OpenAI client (following embedding service pattern)
        
        Args:
            prompt: The prompt to send to ChatGPT
            
        Returns:
            Generated summary or None if failed
        """
        try:
            if not self.client:
                logger.error("OpenAI client not initialized")
                return None
            
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]
            
            # Prepare parameters based on model type
            if 'gpt-5' in self.chat_model.lower():
                # GPT-5 mini special parameters
                response = await self.client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    temperature=0.3,
                    max_completion_tokens=800,  # GPT-5 mini uses max_completion_tokens
                    verbosity='low',  # Concise responses
                    reasoning_effort='minimal'  # Fast reasoning
                )
            else:
                # Standard GPT model parameters
                response = await self.client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=800
                )
            
            # Extract content from response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content and content.strip():
                    logger.info("ChatGPT API call successful")
                    # Post-process to ensure proper bullet point formatting
                    formatted_content = self._format_ai_summary(content.strip())
                    return formatted_content
            
            logger.warning("ChatGPT API returned empty response")
            return None
                
        except Exception as e:
            logger.error(f"ChatGPT API call failed: {e}")
            return None
    
    def _format_ai_summary(self, content: str) -> str:
        """
        Format AI summary to ensure proper bullet point structure with max 3 points, one line each
        
        Args:
            content: Raw AI summary content
            
        Returns:
            Formatted summary with proper line breaks, max 3 bullet points
        """
        try:
            # Split by lines and process each line
            lines = content.split('\n')
            formatted_lines = []
            bullet_count = 0
            max_bullets = 3
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Stop if we already have 3 bullet points
                if bullet_count >= max_bullets:
                    break
                    
                # If line starts with bullet point, keep it as is
                if line.startswith('•'):
                    # Ensure it fits on one line (truncate if too long)
                    if len(line) > 100:  # Limit to 100 characters per line
                        line = line[:97] + '...'
                    formatted_lines.append(line)
                    bullet_count += 1
                # If line looks like a bullet point but doesn't start with •
                elif line.startswith('-') or line.startswith('*'):
                    bullet_text = '• ' + line[1:].strip()
                    if len(bullet_text) > 100:  # Limit to 100 characters per line
                        bullet_text = bullet_text[:97] + '...'
                    formatted_lines.append(bullet_text)
                    bullet_count += 1
                # If line doesn't start with bullet but should be a bullet point
                elif any(keyword in line.lower() for keyword in ['insight', 'pattern', 'trend', 'connection', 'theme', '洞察', '模式', '趋势', '关联', '主题']):
                    # Check if it's likely a bullet point by position or content
                    if len(formatted_lines) > 0 or line.startswith(('This week', 'Your', 'The', '本周', '你的', '这')):
                        bullet_text = '• ' + line
                        if len(bullet_text) > 100:  # Limit to 100 characters per line
                            bullet_text = bullet_text[:97] + '...'
                        formatted_lines.append(bullet_text)
                        bullet_count += 1
                    else:
                        formatted_lines.append(line)
                else:
                    formatted_lines.append(line)
            
            # Join with proper line breaks
            result = '\n'.join(formatted_lines)
            
            # Ensure we have proper bullet points (max 3)
            if not any(line.startswith('•') for line in result.split('\n')):
                # If no bullet points found, try to create them from sentences
                sentences = result.split('. ')
                if len(sentences) > 1:
                    bullet_points = []
                    for i, sentence in enumerate(sentences[:max_bullets]):  # Limit to 3
                        if sentence.strip():
                            bullet_text = '• ' + sentence.strip().rstrip('.')
                            if len(bullet_text) > 100:  # Limit to 100 characters per line
                                bullet_text = bullet_text[:97] + '...'
                            bullet_points.append(bullet_text)
                    result = '\n'.join(bullet_points)
            
            logger.info(f"Formatted AI summary: {len(result)} characters, {len(result.split('•')) - 1} bullet points")
            return result
            
        except Exception as e:
            logger.error(f"Error formatting AI summary: {e}")
            return content  # Return original content if formatting fails
    
    def _get_fallback_summary(self, user_id: str) -> str:
        """
        Get fallback summary when AI is not available
        
        Args:
            user_id: User ID
            
        Returns:
            Fallback summary text
        """
        return f"You captured some new insights this week. Keep building your knowledge base!"
    
    def _get_fallback_summary_from_insights(self, insights: List[Dict[str, Any]]) -> str:
        """
        Get fallback summary based on insights data
        
        Args:
            insights: List of insight objects
            
        Returns:
            Fallback summary text
        """
        insight_count = len(insights)
        
        if insight_count == 0:
            return "No new insights captured this week. Consider adding some content to build your knowledge base!"
        elif insight_count == 1:
            return "You captured 1 new insight this week. Keep building your knowledge base!"
        else:
            # Extract some basic themes from titles
            titles = [insight.get('title', '') for insight in insights if insight.get('title')]
            if titles:
                # Simple theme detection based on common words
                all_words = ' '.join(titles).lower().split()
                word_freq = {}
                for word in all_words:
                    if len(word) > 3:  # Only consider words longer than 3 characters
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get most common words
                common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
                themes = [word for word, freq in common_words if freq > 1]
                
                if themes:
                    return f"You captured {insight_count} new insights this week, with themes around {', '.join(themes)}. Great job expanding your knowledge base!"
                else:
                    return f"You captured {insight_count} new insights this week. Great job expanding your knowledge base!"
            else:
                return f"You captured {insight_count} new insights this week. Great job expanding your knowledge base!"


# Global instance
_ai_summary_service = None

def get_ai_summary_service() -> AISummaryService:
    """Get global AI summary service instance"""
    global _ai_summary_service
    if _ai_summary_service is None:
        _ai_summary_service = AISummaryService()
    return _ai_summary_service
