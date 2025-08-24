from typing import List, Dict, Any, Optional
from langchain.schema import BaseMessage


class ChatState(dict):
    """State for the conversation graph"""
    messages: List[BaseMessage]
    topic: str
    rag_results: Optional[List[Dict[str, Any]]]
    web_results: Optional[List[Dict[str, Any]]]
    current_response: Optional[str]
    search_concepts: Optional[str]
    is_first_message: bool
    topic_category_valid: bool
    is_valid: bool
    # Quiz-related state
    is_quiz_mode: bool
    quiz_questions: Optional[List[Dict[str, Any]]]
    current_quiz_index: Optional[int]
    quiz_scores: Optional[List[Dict[str, Any]]]
    used_quiz_questions: Optional[List[str]]  # Track questions asked across sessions
