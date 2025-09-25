"""
Content generation for weekly digest emails.
Handles user activity analysis, content curation, and template data preparation.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
import logging
import json
from ..utils.timezone_utils import to_utc, now_utc

logger = logging.getLogger(__name__)

class DigestSection:
    """Represents a section in the digest email."""
    def __init__(self, title: str, items: List[Dict[str, Any]], section_type: str = "default"):
        self.title = title
        self.items = items
        self.section_type = section_type  # "highlights", "more", "suggestions", "empty"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "items": self.items,
            "section_type": self.section_type,
            "item_count": len(self.items)
        }

class DigestContentGenerator:
    """Generates personalized digest content for users."""
    
    def __init__(self):
        self.max_highlights = 3
        self.max_additional = 7
        self.max_suggestions = 5
    
    def build_user_digest_payload(
        self,
        user: Dict[str, Any],
        insights: List[Dict[str, Any]],
        stacks: List[Dict[str, Any]],
        no_activity_policy: str = "skip"
    ) -> Dict[str, Any]:
        """
        Build the complete digest payload for a user.
        
        Args:
            user: User information
            insights: User's insights from the past week
            stacks: User's stacks
            no_activity_policy: How to handle users with no activity
        
        Returns:
            Dict containing all digest data for template rendering
        """
        try:
            # Basic user info
            first_name = user.get("first_name") or user.get("name") or "there"
            user_id = user.get("id")
            
            # Analyze activity
            activity_analysis = self._analyze_activity(insights, stacks)
            
            # Handle no activity case
            if activity_analysis["total_activity"] == 0:
                return self._handle_no_activity(user, no_activity_policy)
            
            # Generate content sections
            highlights = self._create_highlights_section(insights)
            more_content = self._create_more_content_section(insights)
            stacks_section = self._create_stacks_section(stacks)
            suggestions = self._create_suggestions_section(insights, stacks)
            
            # Build final payload
            payload = {
                "user": {
                    "id": user_id,
                    "first_name": first_name,
                    "email": user.get("email"),
                    "timezone": user.get("timezone", "America/Los_Angeles")
                },
                "activity_summary": activity_analysis,
                "sections": {
                    "highlights": highlights.to_dict(),
                    "more_content": more_content.to_dict(),
                    "stacks": stacks_section.to_dict(),
                    "suggestions": suggestions.to_dict()
                },
                "metadata": {
                    "generated_at": now_utc().isoformat(),
                    "week_start": activity_analysis.get("week_start"),
                    "week_end": activity_analysis.get("week_end"),
                    "total_insights": len(insights),
                    "total_stacks": len(stacks)
                }
            }
            
            logger.info(f"Generated digest payload for user {user_id}: {activity_analysis['total_activity']} activities")
            return payload
            
        except Exception as e:
            logger.error(f"Error building digest payload for user {user.get('id', 'unknown')}: {e}")
            return self._create_error_payload(user)
    
    def _analyze_activity(self, insights: List[Dict[str, Any]], stacks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user activity to provide insights."""
        total_insights = len(insights)
        total_stacks = len(stacks)
        
        # Categorize insights by type
        url_insights = [i for i in insights if i.get("url")]
        text_insights = [i for i in insights if not i.get("url")]
        
        # Get recent activity (last 3 days)
        recent_cutoff = now_utc() - timedelta(days=3)
        recent_insights = []
        for i in insights:
            created_utc = to_utc(i.get("created_at"))
            updated_utc = to_utc(i.get("updated_at"))
            dt = created_utc or updated_utc
            if dt and dt > recent_cutoff:
                recent_insights.append(i)
        
        # Calculate engagement metrics
        insights_with_summaries = [i for i in insights if self._has_summary(i)]
        insights_with_tags = [i for i in insights if i.get("tags")]
        
        return {
            "total_activity": total_insights + total_stacks,
            "total_insights": total_insights,
            "total_stacks": total_stacks,
            "url_insights": len(url_insights),
            "text_insights": len(text_insights),
            "recent_insights": len(recent_insights),
            "insights_with_summaries": len(insights_with_summaries),
            "insights_with_tags": len(insights_with_tags),
            "engagement_score": self._calculate_engagement_score(insights, stacks),
            "week_start": self._get_week_start(),
            "week_end": self._get_week_end()
        }
    
    def _create_highlights_section(self, insights: List[Dict[str, Any]]) -> DigestSection:
        """Create the highlights section with top insights."""
        # Sort insights by engagement score and recency
        scored_insights = self._score_insights(insights)
        top_insights = scored_insights[:self.max_highlights]
        
        items = []
        for insight in top_insights:
            item = {
                "id": insight.get("id"),
                "title": insight.get("title", "Untitled"),
                "summary": self._get_insight_summary(insight),
                "url": insight.get("url"),
                "image_url": insight.get("image_url"),
                "created_at": insight.get("created_at"),
                "tags": insight.get("tags", []),
                "engagement_score": insight.get("_engagement_score", 0)
            }
            items.append(item)
        
        return DigestSection(
            title="This Week's Highlights",
            items=items,
            section_type="highlights"
        )
    
    def _create_more_content_section(self, insights: List[Dict[str, Any]]) -> DigestSection:
        """Create the additional content section."""
        scored_insights = self._score_insights(insights)
        additional_insights = scored_insights[self.max_highlights:self.max_highlights + self.max_additional]
        
        items = []
        for insight in additional_insights:
            item = {
                "id": insight.get("id"),
                "title": insight.get("title", "Untitled"),
                "url": insight.get("url"),
                "created_at": insight.get("created_at"),
                "tags": insight.get("tags", [])
            }
            items.append(item)
        
        return DigestSection(
            title="More from This Week",
            items=items,
            section_type="more"
        )
    
    def _create_stacks_section(self, stacks: List[Dict[str, Any]]) -> DigestSection:
        """Create the stacks section."""
        if not stacks:
            return DigestSection(
                title="Your Stacks",
                items=[],
                section_type="empty"
            )
        
        items = []
        for stack in stacks[:5]:  # Limit to 5 stacks
            item = {
                "id": stack.get("id"),
                "name": stack.get("name", "Unnamed Stack"),
                "description": stack.get("description", ""),
                "item_count": stack.get("item_count", 0),
                "created_at": stack.get("created_at")
            }
            items.append(item)
        
        return DigestSection(
            title="Your Stacks",
            items=items,
            section_type="stacks"
        )
    
    def _create_suggestions_section(self, insights: List[Dict[str, Any]], stacks: List[Dict[str, Any]]) -> DigestSection:
        """Create suggestions based on user activity."""
        suggestions = []
        
        # Suggest based on patterns
        if len(insights) > 0:
            # Suggest organizing insights into stacks
            if len(stacks) == 0:
                suggestions.append({
                    "type": "feature",
                    "title": "Organize Your Insights",
                    "description": "Create stacks to group related insights together",
                    "action": "Create your first stack",
                    "url": "/my-space?action=create-stack"
                })
            
            # Suggest adding tags
            untagged_insights = [i for i in insights if not i.get("tags")]
            if len(untagged_insights) > 3:
                suggestions.append({
                    "type": "organization",
                    "title": "Add Tags to Your Insights",
                    "description": f"You have {len(untagged_insights)} insights without tags",
                    "action": "Add tags now",
                    "url": "/my-space"
                })
        
        # Suggest based on activity level
        if len(insights) == 0:
            suggestions.append({
                "type": "onboarding",
                "title": "Start Your Knowledge Journey",
                "description": "Save your first insight to begin building your knowledge base",
                "action": "Add an insight",
                "url": "/my-space?action=add-insight"
            })
        elif len(insights) < 5:
            suggestions.append({
                "type": "engagement",
                "title": "Keep Building Your Collection",
                "description": "You're off to a great start! Keep adding insights to build your knowledge base",
                "action": "Add more insights",
                "url": "/my-space"
            })
        
        return DigestSection(
            title="Suggestions for You",
            items=suggestions[:self.max_suggestions],
            section_type="suggestions"
        )
    
    def _handle_no_activity(self, user: Dict[str, Any], policy: str) -> Dict[str, Any]:
        """Handle users with no activity based on their policy."""
        first_name = user.get("first_name") or user.get("name") or "there"
        
        if policy == "skip":
            return {
                "user": {
                    "id": user.get("id"),
                    "first_name": first_name,
                    "email": user.get("email"),
                    "timezone": user.get("timezone", "America/Los_Angeles")
                },
                "activity_summary": {
                    "total_activity": 0,
                    "total_insights": 0,
                    "total_stacks": 0,
                    "url_insights": 0,
                    "text_insights": 0,
                    "recent_insights": 0,
                    "insights_with_summaries": 0,
                    "insights_with_tags": 0,
                    "engagement_score": 0.0,
                    "week_start": self._get_week_start(),
                    "week_end": self._get_week_end(),
                },
                "sections": {
                    "highlights": DigestSection("This Week's Highlights", [], "empty").to_dict(),
                    "more_content": DigestSection("More from This Week", [], "empty").to_dict(),
                    "stacks": DigestSection("Your Stacks", [], "empty").to_dict(),
                    "suggestions": DigestSection("Suggestions for You", [], "empty").to_dict()
                },
                "metadata": {
                    "generated_at": now_utc().isoformat(),
                    "skipped": True,
                    "reason": "no_activity"
                }
            }
        
        elif policy == "brief":
            return {
                "user": {
                    "id": user.get("id"),
                    "first_name": first_name,
                    "email": user.get("email"),
                    "timezone": user.get("timezone", "America/Los_Angeles")
                },
                "activity_summary": {
                    "total_activity": 0,
                    "total_insights": 0,
                    "total_stacks": 0,
                    "url_insights": 0,
                    "text_insights": 0,
                    "recent_insights": 0,
                    "insights_with_summaries": 0,
                    "insights_with_tags": 0,
                    "engagement_score": 0.0,
                    "week_start": self._get_week_start(),
                    "week_end": self._get_week_end(),
                },
                "sections": {
                    "highlights": DigestSection("This Week's Highlights", [], "empty").to_dict(),
                    "more_content": DigestSection("More from This Week", [], "empty").to_dict(),
                    "stacks": DigestSection("Your Stacks", [], "empty").to_dict(),
                    "suggestions": DigestSection("Suggestions for You", [
                        {
                            "type": "engagement",
                            "title": "No Activity This Week",
                            "description": "You haven't added any insights this week. Ready to start building your knowledge base?",
                            "action": "Add your first insight",
                            "url": "/my-space?action=add-insight"
                        }
                    ], "suggestions").to_dict()
                },
                "metadata": {
                    "generated_at": now_utc().isoformat(),
                    "brief_mode": True,
                    "reason": "no_activity_brief"
                }
            }
        
        else:  # policy == "suggestions"
            return {
                "user": {
                    "id": user.get("id"),
                    "first_name": first_name,
                    "email": user.get("email"),
                    "timezone": user.get("timezone", "America/Los_Angeles")
                },
                "activity_summary": {
                    "total_activity": 0,
                    "total_insights": 0,
                    "total_stacks": 0,
                    "url_insights": 0,
                    "text_insights": 0,
                    "recent_insights": 0,
                    "insights_with_summaries": 0,
                    "insights_with_tags": 0,
                    "engagement_score": 0.0,
                    "week_start": self._get_week_start(),
                    "week_end": self._get_week_end(),
                },
                "sections": {
                    "highlights": DigestSection("This Week's Highlights", [], "empty").to_dict(),
                    "more_content": DigestSection("More from This Week", [], "empty").to_dict(),
                    "stacks": DigestSection("Your Stacks", [], "empty").to_dict(),
                    "suggestions": DigestSection("What You Might Have Missed", [
                        {
                            "type": "feature",
                            "title": "Explore Popular Topics",
                            "description": "Discover trending insights and topics in your field",
                            "action": "Browse topics",
                            "url": "/explore"
                        },
                        {
                            "type": "onboarding",
                            "title": "Start Your Knowledge Journey",
                            "description": "Save your first insight to begin building your knowledge base",
                            "action": "Add an insight",
                            "url": "/my-space?action=add-insight"
                        },
                        {
                            "type": "feature",
                            "title": "Organize Your Thoughts",
                            "description": "Create stacks to group related insights together",
                            "action": "Create your first stack",
                            "url": "/my-space?action=create-stack"
                        }
                    ], "suggestions").to_dict()
                },
                "metadata": {
                    "generated_at": now_utc().isoformat(),
                    "suggestions_mode": True,
                    "reason": "no_activity_suggestions"
                }
            }
    
    def _create_error_payload(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback payload when content generation fails."""
        return {
            "user": {
                "id": user.get("id"),
                "first_name": user.get("first_name", "there"),
                "email": user.get("email"),
                "timezone": user.get("timezone", "America/Los_Angeles")
            },
            "activity_summary": {"total_activity": 0},
            "sections": {
                "highlights": DigestSection("This Week's Highlights", [], "empty").to_dict(),
                "more_content": DigestSection("More from This Week", [], "empty").to_dict(),
                "stacks": DigestSection("Your Stacks", [], "empty").to_dict(),
                "suggestions": DigestSection("Suggestions for You", [], "empty").to_dict()
            },
            "metadata": {
                "generated_at": now_utc().isoformat(),
                "error": True,
                "reason": "content_generation_failed"
            }
        }
    
    def _score_insights(self, insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score insights based on engagement and recency."""
        scored = []
        for insight in insights:
            score = self._calculate_engagement_score([insight], [])
            insight["_engagement_score"] = score
            scored.append(insight)
        
        # Sort by score (descending) then by recency
        scored.sort(key=lambda x: (x["_engagement_score"], to_utc(x.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return scored
    
    def _calculate_engagement_score(self, insights: List[Dict[str, Any]], stacks: List[Dict[str, Any]]) -> float:
        """Calculate engagement score for insights."""
        if not insights:
            return 0.0
        
        total_score = 0.0
        for insight in insights:
            score = 0.0
            
            # Base score for having content
            if insight.get("title"):
                score += 1.0
            
            # Bonus for having summary
            if self._has_summary(insight):
                score += 2.0
            
            # Bonus for having tags
            if insight.get("tags"):
                score += 1.0
            
            # Bonus for having URL (external content)
            if insight.get("url"):
                score += 1.0
            
            # Recency bonus
            created_utc = to_utc(insight.get("created_at"))
            if created_utc:
                days_old = (now_utc() - created_utc).days
                if days_old < 1:
                    score += 3.0
                elif days_old < 3:
                    score += 2.0
                elif days_old < 7:
                    score += 1.0
            
            total_score += score
        
        return total_score / len(insights)
    
    def _has_summary(self, insight: Dict[str, Any]) -> bool:
        """Check if insight has a summary."""
        # Check insight_contents for summary
        contents = insight.get("insight_contents", [])
        if contents and isinstance(contents, list) and len(contents) > 0:
            return bool(contents[0].get("summary"))
        
        # Check direct summary field
        return bool(insight.get("summary"))
    
    def _get_insight_summary(self, insight: Dict[str, Any]) -> str:
        """Get the summary text for an insight."""
        # Try insight_contents first
        contents = insight.get("insight_contents", [])
        if contents and isinstance(contents, list) and len(contents) > 0:
            summary = contents[0].get("summary")
            if summary:
                return summary
        
        # Fallback to direct summary field
        summary = insight.get("summary")
        if summary:
            return summary
        
        # Fallback to description
        description = insight.get("description")
        if description:
            return description[:200] + "..." if len(description) > 200 else description
        
        # Fallback to title
        return insight.get("title", "No summary available")
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse datetime string to timezone-aware datetime object."""
        if not dt_str:
            return None
        
        try:
            if dt_str.endswith('Z'):
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00')).astimezone(timezone.utc)
            dt = datetime.fromisoformat(dt_str)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return None
    
    def _get_week_start(self) -> str:
        """Get current week start as ISO string."""
        now = now_utc()
        week_start = now - timedelta(days=now.weekday())
        return week_start.date().isoformat()
    
    def _get_week_end(self) -> str:
        """Get current week end as ISO string."""
        now = now_utc()
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        return week_end.date().isoformat()

