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
        self.model = genai.GenerativeModel("gemini-pro")
        self.last_call_time = 0  # Track last API call

    def generate_response(self, prompt):
        current_time = time.time()
        if current_time - self.last_call_time < 2:  # Avoid rapid consecutive calls
            return "Rate limit: Please wait before making another request."
        self.last_call_time = current_time
        
        response = self.model.generate_content(prompt)
        return response.text if response else "Error generating response."
