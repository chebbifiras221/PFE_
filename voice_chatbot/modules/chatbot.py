from modules.speech import SpeechProcessor
from modules.gemini import GeminiModel
import streamlit as st

class Chatbot:
    def __init__(self):
        self.speech_processor = SpeechProcessor()  # Initialize speech processor module
        self.gemini = GeminiModel()               # Initialize Gemini AI model
        self._init_session_state()                # Initialize session state with conversation history

    def _init_session_state(self):
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []

    def chat(self):
        """Handle single interaction cycle"""
        user_input = self.speech_processor.speech_to_text()
        
        if user_input:
            response = self.gemini.generate_response(user_input)
            audio_path = None
            if not response.startswith("Rate limit") and not response.startswith("I specialize"):
                audio_path = self.speech_processor.text_to_speech(response)
            
            st.session_state.conversation.append(("user", user_input, None))
            st.session_state.conversation.append(("bot", response, audio_path))
            
            print(f"User: {user_input}")
            print(f"AI: {response} | Audio: {audio_path}")
        
        self.stop_chat()
    
    def stop_chat(self):
        self.speech_processor.cleanup()
        st.session_state.chat_active = False
    
    def process_text_input(self, text: str):
        """Handle direct text input"""
        if not text.strip():
            return "Please enter a valid question"
        
        # Reuse your existing Gemini response logic
        return self.gemini.generate_response(text)