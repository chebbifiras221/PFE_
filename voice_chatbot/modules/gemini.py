import time
import logging
import asyncio
from typing import Optional, Dict, Any
import google.generativeai as genai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gemini_api")

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
RATE_LIMIT_SECONDS = 2
MODEL_NAME = "models/gemini-1.5-flash"
VALIDATION_MODEL_NAME = "models/gemini-1.5-flash"  # Can use a smaller model for validation if available

class GeminiModel:
    def __init__(self, api_key: Optional[str] = None, model_name: str = MODEL_NAME):
        """Initialize the Gemini model with API key and configuration.
        
        Args:
            api_key: Optional API key override. If None, uses environment variable.
            model_name: The Gemini model to use.
        """
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError("Missing API key! Set GEMINI_API_KEY in the .env file or pass it to the constructor.")
        
        # Configure the API
        genai.configure(api_key=self.api_key)
        
        # Initialize models
        self.model = genai.GenerativeModel(model_name)
        self.validation_model = genai.GenerativeModel(VALIDATION_MODEL_NAME)
        
        # Rate limiting
        self.last_call_time = 0
        self.rate_limit_seconds = RATE_LIMIT_SECONDS
        
        # Request cache to avoid duplicate requests
        self.cache: Dict[str, Any] = {}
        self.cache_size_limit = 300           # Reasonable limit
        self.cache_ttl = timedelta(hours=12)  # Reasonable TTL
        
        logger.info(f"Initialized GeminiModel with model: {model_name}")

    async def generate_response_async(self, prompt: str) -> str:
        """Asynchronous version of generate_response."""
        # Check cache first
        if prompt in self.cache:
            logger.info("Returning cached response")
            return self.cache[prompt]
            
        # Rate limiting check
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - time_since_last_call
            logger.info(f"Rate limiting: waiting for {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        self.last_call_time = time.time()
        
        # Run validation in a separate thread to not block
        is_valid = await asyncio.to_thread(self._validate_question, prompt)
        
        if not is_valid:
            logger.warning(f"Invalid question rejected: {prompt[:50]}...")
            return "I specialize in programming help. Please ask me about code-related topics!"

        try:
            # Call the Gemini model
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            if not response:
                return "Error: No response generated."
                
            result = response.text
            
            # Cache the result
            self._update_cache(prompt, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Sorry, I encountered an error: {str(e)}"

    def generate_response(self, prompt: str) -> str:
        """Generate a response using the Gemini model.
        
        Args:
            prompt: The text prompt to send to the model.
            
        Returns:
            The model's response as a string.
        """
        # Check cache first
        cached_response = self._get_from_cache(prompt)
        if cached_response:
            logger.info("Returning cached response")
            return cached_response
        
        # Rate limiting check
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.rate_limit_seconds:
            logger.info(f"Rate limiting triggered: {time_since_last_call:.2f}s since last call")
            return f"Please wait {self.rate_limit_seconds - time_since_last_call:.1f} seconds before making another request."
        
        self.last_call_time = current_time
        
        # Validate the question
        if not self._validate_question(prompt):
            logger.info(f"Question validation failed: {prompt[:50]}...")
            return "I specialize in programming help. Please ask me about code-related topics!"

        try:
            # Call the Gemini model
            logger.info(f"Sending prompt to Gemini: {prompt[:50]}...")
            response = self.model.generate_content(prompt)
            
            if not response:
                logger.warning("Empty response received from Gemini")
                return "Error: No response generated."
                
            # Ensure we return a string
            result = response.text if hasattr(response, 'text') else str(response)
            
            # Cache the result
            self._update_cache(prompt, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def _validate_question(self, text: str) -> bool:
        """Validate if the question is related to programming.
        
        Args:
            text: The question text to validate.
        Returns:
            True if the question is programming-related, False otherwise.
        """
        # Quick validation for common programming terms to avoid API calls
        programming_keywords = [
            "code", "program", "function", "class", "algorithm", 
            "javascript", "python", "java", "c++", "html", "css",
            "api", "framework", "library", "error", "bug", "debug",
            "compiler", "interpreter", "syntax", "variable", "object",
            "database", "sql", "http", "request", "response", "server",
            "client", "git", "repository", "commit", "docker", "container",
            "linux", "windows", "macos", "backend", "frontend", "fullstack"
        ]
        
        text_lower = text.lower()
        for keyword in programming_keywords:
            if keyword in text_lower:
                logger.info(f"Keyword match found: {keyword}")
                return True
        
        # For more ambiguous queries, use Gemini's validation
        try:
            validation_prompt = f"""Analyze if this question relates to computer Science/programming/software development (including languages, 
                                frameworks, algorithms, debugging, or development concepts).

                                Consider:
                                1. Explicit mentions of technical terms
                                2. Implied programming context
                                3. Conceptual questions about software development

                                Examples of valid questions:
                                - "How do I handle null pointers?"
                                - "Explain Python's GIL"
                                - "Best practices for React state management"
                                - "What's the difference between programming TCP and UDP?"

                                Examples of invalid questions:
                                - "How to cook pasta?"
                                - "What's the weather today?"
                                - "Explain quantum physics"
                                - "What is math?"

                                Question: {text}

                                Respond ONLY with exactly 'TRUE' or 'FALSE' with no punctuation or explanations."""
            
            # Use validation model with strict configuration
            response = self.validation_model.generate_content(
                validation_prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 5  # Slightly increased for reliability
                }
            )
            
            result = "true" in response.text.lower().strip()
            logger.info(f"Validation result for '{text[:30]}...': {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            # If validation fails, default to accepting the question
            return True
    
    def _update_cache(self, prompt: str, response: str) -> None:
        """Update cache with basic timestamp."""
        # Simple cache entry with timestamp
        self.cache[prompt] = {
            'response': response,
            'timestamp': datetime.now()
        }
        
        # Remove expired entries and maintain size limit
        if len(self.cache) > self.cache_size_limit:
            current_time = datetime.now()
            # Remove expired and excess entries in one pass
            self.cache = {
                k: v for k, v in self.cache.items()
                if current_time - v['timestamp'] <= self.cache_ttl
            }
            
            # If still over limit, remove oldest entries
            while len(self.cache) > self.cache_size_limit:
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k]['timestamp'])
                self.cache.pop(oldest_key)

    def _get_from_cache(self, prompt: str) -> Optional[str]:
        """Get response from cache with TTL check."""
        if prompt in self.cache:
            entry = self.cache[prompt]
            if datetime.now() - entry['timestamp'] <= self.cache_ttl:
                return entry['response']
            self.cache.pop(prompt)  # Remove expired entry
        return None
