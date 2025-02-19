import google.generativeai as genai

genai.configure(api_key="AIzaSyDekpdYnC9wlHURth7ducxhWqE8xcHY8ZQ")

class GeminiModel:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")

    def generate_response(self, prompt):
        response = self.model.generate_content(prompt)
        return response.text if response else "Error generating response."
