from modules.speech import SpeechProcessor
from modules.gemini import GeminiModel

class Chatbot:
    def __init__(self):
        self.speech_processor = SpeechProcessor()
        self.gemini = GeminiModel()

    def chat(self):
        print("Say 'exit' to stop.")
        while True:
            user_input = self.speech_processor.speech_to_text()
            print("User:", user_input)
            if "exit" in user_input.lower():
                print("Chatbot: Goodbye!")
                self.speech_processor.text_to_speech("Goodbye!")
                break
            response = self.gemini.generate_response(user_input)
            print("Chatbot:", response)
            self.speech_processor.text_to_speech(response)
