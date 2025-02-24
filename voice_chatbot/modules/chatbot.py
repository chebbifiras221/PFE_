from modules.speech import SpeechProcessor
from modules.gemini import GeminiModel
import streamlit as st

class Chatbot:
    def __init__(self):
        self.speech_processor = SpeechProcessor() # Initialize speech processor module
        self.gemini = GeminiModel()               # Initialize Gemini AI model
        self._init_session_state()                # Initialize session state with conversation history

    def _init_session_state(self):
        # Check if the session state has the key 'conversation'
        # If it doesn't, it will be created and initialized an empty list
        if 'conversation' not in st.session_state:
            # The session state is like a dictionary that stores values across multiple runs of your Streamlit app
            # The key is 'conversation', and the value is an empty list
            st.session_state.conversation = []

    def chat(self):
        """Handle single interaction cycle"""
        user_input = self.speech_processor.speech_to_text()
        
        if user_input:
            # Terminal display
            print(f"User: {user_input}")
            
            # Get and display response
            response = self.gemini.generate_response(user_input)
            audio_path = self.speech_processor.text_to_speech(response)
            
            # Browser display
            st.session_state.conversation.append(("user", user_input)) # Store user input
            st.session_state.conversation.append(("bot", response, audio_path)) # Store ai output
            
            # Convert response to speech
            self.speech_processor.text_to_speech(response)

            # Terminal display
            print(f"User: {user_input}")
            print(f"AI: {response} | Audio: {audio_path}")
        
        # Always stop after one interaction
        self.stop_chat()
    
    def stop_chat(self):
        # Reset speech components
        self.speech_processor.cleanup() 
        # Set the chat_active flag in the session state to False, indicating the chat has stopped
        st.session_state.chat_active = False
