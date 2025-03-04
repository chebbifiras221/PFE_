import whisper
import pyaudio
import wave
import numpy as np
import os
import time
from datetime import datetime
from gtts import gTTS  # New import for Google TTS
import requests  # For handling network errors with gTTS

# Fix Windows path handling for Whisper
import sys
import ctypes

if sys.platform == "win32":
    # Bypass Unix-specific checks (important for handling Whisper on Windows)
    ctypes.CDLL._name = "_not_a_real_path_.dll"

# Now import Whisper
import whisper

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
        self.SILENCE_TIMEOUT = 2  # Seconds of silence to stop recording

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
        """Convert text to speech with Google TTS and timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.audio_dir, f"response_{timestamp}.mp3")
        
        try:
            # Generate speech with gTTS (lang='en' for English, tld='com' for American accent)
            tts = gTTS(text=text, lang='en', tld=accent)
            tts.save(filename)  # Save to file
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