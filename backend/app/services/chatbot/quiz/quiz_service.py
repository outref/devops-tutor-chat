from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage
import logging
import json
import re
import random

logger = logging.getLogger(__name__)


class QuizService:
    """Service for generating and processing quiz questions"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    async def generate_quiz_questions(self, messages: List[BaseMessage], topic: str, 
                                    used_questions: List[str] = None) -> List[Dict[str, Any]]:
        """Generate quiz questions based on conversation history"""
        if used_questions is None:
            used_questions = []
        
        logger.info(f"Starting quiz generation with {len(used_questions)} previously used questions")
        
        # Build conversation context
        conversation_history = []
        for msg in messages[:-1]:  # Exclude the quiz request message
            if isinstance(msg, HumanMessage):
                conversation_history.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                conversation_history.append(f"Assistant: {msg.content[:200]}...")  # Truncate long responses
        
        context = "\n".join(conversation_history)
        
        # Generate quiz questions
        quiz_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are creating an interactive quiz based on the conversation history. You MUST respond with ONLY a valid JSON array, nothing else.

Generate 5 COMPLETELY DIFFERENT quiz questions that test understanding of the concepts discussed.

CRITICAL REQUIREMENTS:
- Questions MUST be directly related to what was discussed in the conversation
- Create DIVERSE questions covering different aspects of the topic
- Mix question types: multiple choice, true/false, and short answer
- Test understanding and application, NOT just memorization
- Questions should be SIGNIFICANTLY DIFFERENT from any previously asked questions

AVOID REPETITION: Do NOT create questions similar to previously asked ones. If previous questions exist, create questions about different aspects, use different wording, focus on different concepts, or ask about related but distinct topics.

JSON FORMAT REQUIRED:
[
  {{
    "question": "What is the main purpose of Docker containers?",
    "type": "multiple_choice", 
    "options": ["Virtual machine replacement", "Application containerization", "Network management", "Storage solutions"],
    "correct_answer": "Application containerization",
    "explanation": "Docker containers provide lightweight containerization for applications."
  }}
]

CRITICAL: 
- For multiple choice: options array MUST contain ONLY plain text, NO letter prefixes like "A.", "B.", "C.", "D."
- WRONG: "options": ["A. Virtual machines", "B. Containers"] 
- CORRECT: "options": ["Virtual machines", "Containers"]

Return ONLY the JSON array. No explanations, no markdown, no code blocks.

Previously asked questions to AVOID repeating:
""" + ("\n- " + "\n- ".join(used_questions) if used_questions else "None")),
            ("user", f"Topic: {topic}\n\nConversation History:\n{context}\n\nGenerate 5 NEW and DIFFERENT quiz questions as JSON:")
        ])
        
        response = await self.llm.ainvoke(quiz_prompt.format_messages())
        
        try:
            # Log the raw response for debugging
            logger.info(f"Raw quiz generation response: {response.content[:500]}...")
            
            # Extract JSON from response with multiple strategies
            json_str = response.content.strip()
            
            # Strategy 1: Look for JSON code block
            if "```json" in json_str.lower():
                json_match = re.search(r'```json\s*(.*?)\s*```', json_str, re.DOTALL | re.IGNORECASE)
                if json_match:
                    json_str = json_match.group(1).strip()
            elif "```" in json_str:
                json_match = re.search(r'```\s*(.*?)\s*```', json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
            
            # Strategy 2: Look for array starting with [
            if not json_str.startswith('['):
                array_match = re.search(r'\[.*\]', json_str, re.DOTALL)
                if array_match:
                    json_str = array_match.group(0)
            
            logger.info(f"Extracted JSON string: {json_str[:200]}...")
            
            # Parse JSON
            quiz_questions = json.loads(json_str)
            
            # Validate structure
            if not isinstance(quiz_questions, list):
                raise ValueError("Quiz questions should be a list")
            
            if len(quiz_questions) == 0:
                raise ValueError("No quiz questions generated")
            
            # Ensure we have at most 5 questions
            if len(quiz_questions) > 5:
                quiz_questions = quiz_questions[:5]
            
            # Validate and normalize each question
            for i, q in enumerate(quiz_questions):
                if not isinstance(q, dict):
                    raise ValueError(f"Question {i+1} is not a dictionary")
                if "question" not in q:
                    raise ValueError(f"Question {i+1} missing 'question' field")
                
                # Normalize field names and add missing fields
                if "answer" in q and "correct_answer" not in q:
                    q["correct_answer"] = q["answer"]
                    del q["answer"]
                
                if "correct_answer" not in q:
                    raise ValueError(f"Question {i+1} missing answer field")
                
                # Add type based on presence of options
                if "type" not in q:
                    if "options" in q and len(q.get("options", [])) > 0:
                        q["type"] = "multiple_choice"
                    else:
                        q["type"] = "short_answer"
                
                # Randomize multiple choice options to distribute correct answers
                if q["type"] == "multiple_choice" and "options" in q:
                    options = q["options"]
                    correct_text = q["correct_answer"]
                    
                    # Clean options by removing any existing letter prefixes (A., B., etc.)
                    cleaned_options = []
                    for option in options:
                        # Remove letter prefixes like "A. ", "B. ", etc.
                        cleaned_option = re.sub(r'^[A-D]\.\s*', '', option.strip())
                        cleaned_options.append(cleaned_option)
                    
                    # Create a list of (option_text, is_correct) tuples
                    option_tuples = []
                    for option in cleaned_options:
                        # Check if this option matches the correct answer
                        is_correct = (option.strip().lower() == correct_text.strip().lower() or 
                                    correct_text.strip().lower() in option.strip().lower() or 
                                    option.strip().lower() in correct_text.strip().lower())
                        option_tuples.append((option, is_correct))
                    
                    # Shuffle the options
                    random.shuffle(option_tuples)
                    
                    # Rebuild the options list and find new correct answer position
                    shuffled_options = []
                    new_correct_letter = None
                    
                    for idx, (option_text, is_correct) in enumerate(option_tuples):
                        shuffled_options.append(option_text)
                        if is_correct:
                            new_correct_letter = chr(65 + idx)  # A, B, C, D
                    
                    # Update the question with cleaned and shuffled options
                    q["options"] = shuffled_options
                    if new_correct_letter:
                        q["correct_answer"] = new_correct_letter
                        logger.info(f"Question {i+1}: Randomized options, correct answer is now '{new_correct_letter}'")
                    else:
                        # Fallback - set first option as correct
                        q["correct_answer"] = "A"
                        logger.warning(f"Question {i+1}: Could not identify correct option after shuffle, defaulting to 'A'")
                
                # Add default explanation if missing
                if "explanation" not in q:
                    q["explanation"] = f"This question tests your understanding of the concepts discussed about {topic}."
            
            logger.info(f"Successfully generated {len(quiz_questions)} quiz questions")
            return quiz_questions
            
        except Exception as e:
            logger.error(f"Error parsing quiz questions: {e}")
            logger.error(f"Raw response was: {response.content}")
            
            # Fallback: Generate a simple quiz question manually
            fallback_questions = [
                {
                    "question": f"Based on our discussion about {topic}, what is the main benefit of this technology?",
                    "type": "short_answer",
                    "correct_answer": "Various benefits including efficiency, automation, and scalability",
                    "explanation": "This technology provides multiple advantages in modern development and operations."
                }
            ]
            
            return fallback_questions
    
    async def process_quiz_answer(self, current_question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """Process user's quiz answer and provide feedback"""
        logger.info(f"Processing quiz answer: {user_answer}")
        
        # Evaluate the answer
        evaluation_prompt = ChatPromptTemplate.from_messages([
            ("system", """Evaluate the user's answer to the quiz question. Be encouraging and educational.

Question: {question}
Question Type: {q_type}
Correct Answer: {correct_answer}
User Answer: {user_answer}

CRITICAL: You must start your response with EXACTLY one of these:
- "CORRECT:" if the answer is right
- "INCORRECT:" if the answer is wrong

For multiple choice questions:
- Compare the user's letter (A, B, C, D) with the option that matches the correct answer
- Be flexible: accept both letter answers and full text answers
- "A", "B", "C", "D" should be treated as selecting that option

For short answer questions:
- Be flexible and accept answers that demonstrate understanding
- Look for key concepts rather than exact wording

Format your response as:
CORRECT: [Brief explanation and educational insight]
OR
INCORRECT: The correct answer is [correct answer]. [Brief explanation and educational insight]"""),
            ("user", "Evaluate this answer")
        ])
        
        # Build context for evaluation
        question_context = current_question["question"]
        if current_question["type"] == "multiple_choice" and "options" in current_question:
            options = current_question["options"]
            options_text = "\n".join([f"{chr(65 + i)}. {option}" for i, option in enumerate(options)])
            question_context = f"{current_question['question']}\n\nOptions:\n{options_text}"
        
        response = await self.llm.ainvoke(
            evaluation_prompt.format_messages(
                question=question_context,
                q_type=current_question["type"],
                correct_answer=current_question["correct_answer"],
                user_answer=user_answer
            )
        )
        
        # Parse evaluation
        evaluation = response.content.strip()
        is_correct = evaluation.upper().startswith("CORRECT:")
        
        logger.info(f"Evaluation response: {evaluation[:100]}...")
        logger.info(f"Parsed as correct: {is_correct}")
        
        return {
            "is_correct": is_correct,
            "feedback": evaluation
        }
    
    def format_quiz_question(self, question: Dict[str, Any], number: int, total: int = 5) -> str:
        """Format a quiz question for display"""
        q_type = question["type"]
        q_text = f"**Question {number}/{total}:** {question['question']}\n\n"
        
        if q_type == "multiple_choice":
            options = question.get("options", [])
            for i, option in enumerate(options):
                q_text += f"{chr(65 + i)}. {option}\n"
            q_text += "\n*Please enter your answer (A, B, C, or D)*"
        elif q_type == "true_false":
            q_text += "*Please answer True or False*"
        else:  # short_answer
            q_text += "*Please provide a brief answer*"
        
        return q_text
