import time
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Missing API key! Set GEMINI_API_KEY in the .env file.")

genai.configure(api_key=API_KEY)

class GeminiModel:
    def __init__(self):
        #model initialization
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")
        self.last_call_time = 0

    def generate_response(self, prompt):
        current_time = time.time()
        if current_time - self.last_call_time < 2:  # Avoid rapid consecutive calls
            return "Rate limit: Please wait before making another request."
        self.last_call_time = current_time
        
        # Add validation check first
        if not self._validate_question(prompt):
            return "I specialize in programming help. Ask me about code-related topics!"

        response = self.model.generate_content(prompt)
        return response.text if response else "Error generating response."
    
    def _validate_question(self, text: str) -> bool:
        # Validate using Gemini's understanding of programming concepts
        validation_prompt = f"""Analyze if this question relates to programming/software development (including languages, 
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
        
            # Use main model but with stricter config
        response = self.model.generate_content(
            validation_prompt,
            generation_config={
                "temperature": 0.0, # A temperature of 0.0 means that the model will generate text in a deterministic way, without any randomness or creativity.
                "max_output_tokens": 1 # Only respond with a single token, either "true" or "false"
            }
        )
        return "true" in response.text.lower().strip()