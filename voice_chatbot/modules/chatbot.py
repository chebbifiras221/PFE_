from modules.speech import SpeechProcessor
from modules.gemini import GeminiModel
from modules.history_manager import HistoryManager
from modules.utils import TimingStats, measure_time
import streamlit as st
import time
import logging

class Chatbot:
    def __init__(self):
        with measure_time() as get_startup_time:
            self.speech_processor = SpeechProcessor()
            self.gemini = GeminiModel()
            self.history_manager = HistoryManager()
            self.timing_stats = TimingStats()
            self._init_session_state()
            
        self.timing_stats.startup_time = get_startup_time()
        print(f"Startup time: {self.timing_stats.format_time(self.timing_stats.startup_time)}")

    def _init_session_state(self):
        if 'conversation' not in st.session_state:
            st.session_state.conversation = []

    def chat(self):
        """Handle single interaction cycle"""
        with measure_time() as get_response_time:
            result = self.speech_processor.speech_to_text()
            
            if result and result["text"]:
                user_input = result["text"]
                audio_path = result["audio_file"]

                response = self.gemini.generate_response(user_input)
                response_audio = None
                if not response.startswith("Rate limit") and not response.startswith("I specialize"):
                    response_audio = self.speech_processor.text_to_speech(response)
                
                current_conversation = [
                    ("user", user_input, audio_path),
                    ("bot", response, response_audio)
                ]
                
                self.history_manager.save_conversation(current_conversation)
                st.session_state.conversation.extend(current_conversation)
        
        response_time = get_response_time()
        self.timing_stats.last_response_time = response_time
        self.timing_stats.response_times.append(response_time)
    
    def stop_chat(self):
        self.speech_processor.cleanup()
        st.session_state.chat_active = False
    
    def process_text_input(self, text: str):
        """Handle direct text input"""
        if not text.strip():
            return "Please enter a valid question", 0, None
        
        total_start_time = time.time()
        
        # Generate text response
        with measure_time() as get_response_time:
            response = self.gemini.generate_response(text)
        
        response_time = get_response_time()
        self.timing_stats.last_response_time = response_time
        self.timing_stats.response_times.append(response_time)
        
        # Generate audio
        audio_path = None
        if response and not response.startswith("Rate limit") and not response.startswith("I specialize"):
            with measure_time() as get_audio_time:
                audio_path = self.speech_processor.text_to_speech(response)
            
            audio_time = get_audio_time()
            self.timing_stats.last_audio_time = audio_time
            self.timing_stats.audio_times.append(audio_time)
        else:
            audio_time = 0
            self.timing_stats.last_audio_time = audio_time
            self.timing_stats.audio_times.append(audio_time)
        
        # Calculate total time
        total_time = time.time() - total_start_time
        self.timing_stats.last_total_time = total_time
        self.timing_stats.total_times.append(total_time)
        
        # Log timing information
        logger = logging.getLogger(__name__)
        logger.info(f"Response generation time: {response_time:.2f}s")
        logger.info(f"Audio generation time: {audio_time:.2f}s")
        logger.info(f"Total processing time: {total_time:.2f}s")
        
        current_conversation = [
            ("user", text, None),
            ("bot", response, audio_path)
        ]
        self.history_manager.save_conversation(current_conversation)
        
        return response, response_time, audio_path
