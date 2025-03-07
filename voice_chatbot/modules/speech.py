import whisper
import pyaudio
import wave
import numpy as np
import os
import time
from datetime import datetime
from gtts import gTTS  # New import for Google TTS
import requests  # For handling network errors with gTTS
import re

# Fix Windows path handling for Whisper
import sys
import ctypes

if sys.platform == "win32":
    # Bypass Unix-specific checks (important for handling Whisper on Windows)
    ctypes.CDLL._name = "_not_a_real_path_.dll"

class SpeechProcessor:
    def __init__(self):
        self.audio_dir = "audio_history"
        self.model = whisper.load_model("base")  # Load Whisper model
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Audio recording parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 512
        self.SILENCE_TIMEOUT = 5  # Seconds of silence to stop recording

    def speech_to_text(self):
        """Record audio and transcribe using Whisper"""
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        try:
            print("Listening...")
            frames = []
            silent_chunks = 0
            threshold = 500  # Audio threshold for silence detection

            while True:
                data = stream.read(self.CHUNK)
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Check for silence
                if np.abs(audio_data).mean() < threshold:
                    silent_chunks += 1
                    if silent_chunks > self.SILENCE_TIMEOUT * (self.RATE / self.CHUNK):
                        break
                else:
                    silent_chunks = 0

        except Exception as e:
            print(f"Recording error: {str(e)}")
            return None
        finally:
            # Cleanup recording resources
            stream.stop_stream()
            stream.close()
            audio.terminate()

            # Save temporary audio file
            filename = os.path.join(self.audio_dir, f"temp_{int(time.time())}.wav")
            self._save_wav(frames, filename)
            
            # Transcribe using Whisper
            return self._transcribe_audio(filename)

    def _save_wav(self, frames, filename):
        """Save recorded audio to WAV file"""
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(frames))

    def _transcribe_audio(self, filename):
        """Transcribe audio file using Whisper"""
        try:
            result = self.model.transcribe(filename)
            os.remove(filename)  # Cleanup temp file
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return None

    def text_to_speech(self, text, accent='com'):
        """Convert preprocessed text to speech with Google TTS."""
        preprocessed_text = self.preprocess_text(text)
        if not preprocessed_text.strip():
            preprocessed_text = "The response contains only code or formatting, which I've omitted."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.audio_dir, f"response_{timestamp}.mp3")

        try:
            tts = gTTS(text=preprocessed_text, lang='en', tld=accent)
            tts.save(filename)
            return filename
        except requests.ConnectionError:
            print("Network error: Could not connect to TTS service.")
            return None
        except Exception as e:
            print(f"TTS error: {e}")
            return None

    def cleanup(self):
        """Reset speech components"""
        pass  # No cleanup required for gTTS

    def preprocess_text(self, text):
        """Preprocess text to remove code blocks, handle Markdown elements, and clean up for TTS."""
        # Handle multi-line elements that should be removed entirely
        # Remove code blocks (```...```), including multi-line and nested content
        text = re.sub(r'```[\s\S]*?```', '', text, flags=re.DOTALL)

        # Remove images (e.g., ![alt text](url)), including malformed ones
        text = re.sub(r'!\[(.*?)\]\((.*?)\)', '', text)

        # Handle inline elements
        # Handle links: extract text part (e.g., [text](url) -> text), even with nested ] if escaped
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)

        # Handle inline code with single or double backticks (e.g., `code` or ``code with ` inside``)
        # First, handle double backticks
        text = re.sub(r'``(.*?)``', r'\1', text)
        # Then single backticks (non-greedy to avoid over-matching)
        text = re.sub(r'`([^`]*?)`', r'\1', text)

        # Remove bold and italic formatting, handling nested cases
        # Bold (e.g., **bold** or __bold__)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        # Italic (e.g., *italic* or _italic_)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)

        # Process line-based elements
        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Remove horizontal rules (e.g., ---, ***, ___ with optional spaces)
            if re.match(r'^\s*[-*_]{3,}\s*$', line):
                continue

            # Handle headers (e.g., # Header or ## Header ##)
            line = re.sub(r'^#+(\s+|$)', '', line)  # Remove leading # and space
            line = re.sub(r'\s#+$', '', line)       # Remove trailing #

            # Handle list items (unordered: -/*, ordered: 1./1) with optional indentation
            line = re.sub(r'^\s*[-*]\s+', '', line)       # Unordered lists
            line = re.sub(r'^\s*\d+\.\s+', '', line)      # Ordered lists

            # Handle blockquotes (e.g., > Quote or >> Nested), possibly multi-line
            line = re.sub(r'^>+(\s+|$)', '', line)

            # Handle tables: identify potential table rows and process
            if '|' in line and not re.match(r'^[-\s|]+$', line):  # Exclude separator lines
                # Replace | with spaces, preserving cell content
                line = re.sub(r'\s*\|\s*', ' ', line).strip()
            elif re.match(r'^[-\s|]+$', line):  # Table separator line
                continue  # Remove separator lines like |---|---|

            processed_lines.append(line)

        # Reconstruct text and clean up
        text = '\n'.join(processed_lines)
        # Normalize whitespace: collapse multiple newlines and spaces
        text = re.sub(r'\n\s*\n+', '\n', text).strip()
        text = re.sub(r'\s+', ' ', text)

        return text