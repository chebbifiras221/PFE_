import whisper
import pyaudio
import wave
import numpy as np
import os
import time
from datetime import datetime
import pyttsx3

# Fix Windows path handling for Whisper
import sys
import ctypes

if sys.platform == "win32":
    # Bypass Unix-specific checks (and for some reason important for handeling Whisper for Windows)
    ctypes.CDLL._name = "_not_a_real_path_.dll" 

class SpeechProcessor:
    def __init__(self):
        # Initialize the TTS engine
        self.engine = pyttsx3.init()
        # Directory to store audio history
        self.audio_dir = "audio_history"
        # Load the 'base' Whisper model
        self.model = whisper.load_model("base")
        # Create the directory if it doesn't exist
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Audio recording parameters
        # Audio format
        self.FORMAT = pyaudio.paInt16
        # Number of channels
        self.CHANNELS = 1
        # Sample rate (low quality for now aka 16kHz)
        self.RATE = 16000
        # Chunk size
        self.CHUNK = 512
        # Number of seconds of silence to stop recording
        self.SILENCE_TIMEOUT = 5

    def speech_to_text(self):
        """Record audio and transcribe using Whisper"""
        audio = pyaudio.PyAudio()           # Initialize PyAudio object
        stream = audio.open(                # Open a new stream for audio input
            format=self.FORMAT,             # Set the audio format
            channels=self.CHANNELS,         # Set the number of input channels
            rate=self.RATE,                 # Set the sample rate
            input=True,                     # Specify that this is an input stream
            frames_per_buffer=self.CHUNK    # Set the buffer size for each frame
        )

        try:
            # Notify user that listening has started (in the terminal)
            print("Listening...")
            # Initialize list to store audio frames
            frames = []
            # Counter for silent chunks
            silent_chunks = 0
            # Set threshold for detecting silence
            threshold = 1000

            # Continuously read audio data
            while True:
                # Read a chunk of audio data from stream
                data = stream.read(self.CHUNK)
                # Append audio data to frames list
                frames.append(data)
                # Convert audio data to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Check if the audio is silent
                if np.abs(audio_data).mean() < threshold:
                    # Increment silent chunks counter
                    silent_chunks += 1
                    # Break loop if silence duration exceeds timeout
                    if silent_chunks > self.SILENCE_TIMEOUT * (self.RATE/self.CHUNK):
                        break
                else:
                    # Reset silent chunks counter if sound is detected
                    silent_chunks = 0

        except Exception as e:
            # Print error message if recording fails
            print(f"Recording error: {str(e)}") 
            return None                         # Return None if recording fails
        finally:                                # Cleanup recording resources
            stream.stop_stream()                # Stop stream
            stream.close()                      # Close stream
            audio.terminate()                   # Terminate audio

            # Save temporary audio file
            filename = os.path.join(self.audio_dir, f"temp_{int(time.time())}.wav")  # Generate filename
            self._save_wav(frames, filename)                                         # Save audio file
            
            # Transcribe using Whisper
            return self._transcribe_audio(filename)

    def _save_wav(self, frames, filename):
        """Save recorded audio to WAV file"""
        # Open file in write binary mode
        with wave.open(filename, 'wb') as wf:
            # Set number of channels
            wf.setnchannels(self.CHANNELS)
            # Set sample width
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
            # Set frame rate
            wf.setframerate(self.RATE)
            # Write frames to file
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

    def text_to_speech(self, text):
        """Convert text to speech with timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.audio_dir, f"response_{timestamp}.mp3")
        self.engine.save_to_file(text, filename)
        self.engine.runAndWait()
        return filename

    def cleanup(self):
        """Reset speech components"""
        self.engine.stop()