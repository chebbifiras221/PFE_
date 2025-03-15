import whisper
import pyaudio
import wave
import numpy as np
import os
import time
import logging
from datetime import datetime
from gtts import gTTS
import requests
import re
import threading
from pathlib import Path
import sys
import ctypes
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("speech_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SpeechProcessor")

# Fix Windows path handling for Whisper
if sys.platform == "win32":
    # Bypass Unix-specific checks for Whisper on Windows
    ctypes.CDLL._name = "_not_a_real_path_.dll"

class SpeechProcessor:
    def __init__(self, model_size="base", audio_dir="audio_history", language="en"):
        """
        Initialize the speech processor with configurable parameters.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            audio_dir: Directory to store audio files
            language: Default language for TTS
        """
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        self.language = language
        
        # Audio recording parameters
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK = 1024  # Increased for better performance
        self.SILENCE_TIMEOUT = 2.5  # Reduced for faster response
        self.SILENCE_THRESHOLD = 10  # Configurable threshold
        
        # Background cleanup for old audio files
        threading.Thread(target=self._cleanup_old_files, daemon=True).start()

    def speech_to_text(self, timeout=30, device_index=None):
        """
        Record audio and transcribe using Whisper.
        
        Args:
            timeout: Maximum recording time in seconds
            device_index: Specific audio input device to use
            
        Returns:
            Transcribed text or None if error
        """
        audio = pyaudio.PyAudio()
        
        # List available input devices if debugging
        if logger.level <= logging.DEBUG:
            self._list_audio_devices(audio)
            
        try:
            stream = audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK
            )
            
            logger.info("Listening...")
            frames = []
            silent_chunks = 0
            max_chunks = int(timeout * (self.RATE / self.CHUNK))
            recording_started = False
            
            for _ in range(max_chunks):
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                audio_level = np.abs(audio_data).mean()
                
                # Start recording when sound is detected
                if audio_level >= self.SILENCE_THRESHOLD:
                    if not recording_started:
                        logger.debug(f"Recording started (level: {audio_level})")
                        recording_started = True
                    frames.append(data)
                    silent_chunks = 0
                elif recording_started:
                    frames.append(data)  # Keep some silence for natural pauses
                    silent_chunks += 1
                    
                    # Stop if silence exceeds threshold
                    if silent_chunks > self.SILENCE_TIMEOUT * (self.RATE / self.CHUNK):
                        logger.debug(f"Silence detected, stopping recording")
                        break
                        
            # Don't process if nothing meaningful was recorded
            if not recording_started or len(frames) < 3:
                logger.info("No speech detected")
                return None
                
        except Exception as e:
            logger.error(f"Recording error: {str(e)}")
            return None
        finally:
            # Cleanup recording resources
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
        # Only save and transcribe if we have recorded data
        if frames:
            timestamp = int(time.time())
            filename = self.audio_dir / f"input_{timestamp}.wav"
            self._save_wav(frames, filename)

            # Return both text and audio file path
            transcription = self._transcribe_audio(filename)
            return {
                "text": transcription,
                "audio_file": str(filename)
            }
        return None
            
    def _list_audio_devices(self, audio):
        """List available audio input devices for debugging"""
        info = audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                logger.debug(f"Input Device {i}: {device_info.get('name')}")

    def _save_wav(self, frames, filename):
        """Save recorded audio to WAV file"""
        try:
            with wave.open(str(filename), 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(frames))
            logger.debug(f"Audio saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving audio: {e}")

    def _transcribe_audio(self, filename):
        """Transcribe audio file using Whisper with error handling"""
        try:
            logger.info(f"Transcribing {filename}")
            # Add options for better transcription
            result = self.model.transcribe(
                str(filename),
                fp16=False,  # Better compatibility
                language=self.language
            )
            return result["text"].strip()
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None

    def text_to_speech(self, text, accent='com', speed=1.0):
        """
        Convert preprocessed text to speech with Google TTS.
        
        Args:
            text: Text to convert to speech
            accent: TLD for Google TTS accent (com, co.uk, etc.)
            speed: Speech rate (0.5-2.0)
            
        Returns:
            Path to the generated audio file or None if error
        """
        preprocessed_text = self.preprocess_text(text)
        if not preprocessed_text.strip():
            preprocessed_text = "The response contains only code or formatting, which I've omitted."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.audio_dir / f"response_{timestamp}.mp3"

        # Split long text into manageable chunks (gTTS has limitations)
        max_chars = 5000
        text_chunks = self._chunk_text(preprocessed_text, max_chars)
        
        try:
            if len(text_chunks) == 1:
                # Simple case - single chunk
                tts = gTTS(text=text_chunks[0], lang=self.language, tld=accent, slow=(speed < 1.0))
                tts.save(str(filename))
            else:
                # Multiple chunks need to be combined
                temp_files = []
                for i, chunk in enumerate(text_chunks):
                    temp_file = self.audio_dir / f"temp_chunk_{timestamp}_{i}.mp3"
                    tts = gTTS(text=chunk, lang=self.language, tld=accent, slow=(speed < 1.0))
                    tts.save(str(temp_file))
                    temp_files.append(str(temp_file))
                
                # Combine audio files using ffmpeg if available, otherwise keep the first chunk
                if self._combine_audio_files(temp_files, str(filename)):
                    # Cleanup temp files
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                else:
                    # Fallback if combining failed
                    filename = Path(temp_files[0])
                    logger.warning("Could not combine audio chunks, using first chunk only")
            
            logger.info(f"Text-to-speech saved to {filename}")
            return str(filename)
        except requests.ConnectionError:
            logger.error("Network error: Could not connect to TTS service")
            return None
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    def _combine_audio_files(self, input_files, output_file):
        """Combine multiple audio files into one if ffmpeg is available"""
        try:
            import subprocess
            # Create a file list for ffmpeg
            list_file = self.audio_dir / "filelist.txt"
            with open(list_file, 'w') as f:
                for file in input_files:
                    f.write(f"file '{file}'\n")
            
            # Use ffmpeg to concatenate files
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                "-i", str(list_file), "-c", "copy", output_file
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            os.remove(list_file)
            return True
        except Exception as e:
            logger.error(f"Error combining audio files: {e}")
            return False

    def _chunk_text(self, text, max_chars):
        """Split text into chunks of maximum size, trying to break at sentences"""
        if len(text) <= max_chars:
            return [text]
            
        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
                
            # Try to find a sentence break
            split_pos = max_chars
            for sep in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                pos = text[:max_chars].rfind(sep)
                if pos > 0:  # Found a good break point
                    split_pos = pos + len(sep) - 1
                    break
                    
            chunks.append(text[:split_pos].strip())
            text = text[split_pos:].strip()
            
        return chunks

    def cleanup(self):
        """Reset speech components and cleanup resources"""
        logger.info("Cleaning up resources")
        # Nothing specific to clean up with current implementation

    def _cleanup_old_files(self, max_age_days=7):
        """Background task to clean up old audio files"""
        try:
            # Wait a bit before starting cleanup
            time.sleep(10)
            logger.info(f"Starting background cleanup of files older than {max_age_days} days")
            
            cutoff_time = time.time() - (max_age_days * 86400)
            count = 0
            
            for file_path in self.audio_dir.glob("*.mp3"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    count += 1
                    
            for file_path in self.audio_dir.glob("*.wav"):
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    count += 1
                    
            if count > 0:
                logger.info(f"Cleaned up {count} old audio files")
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")

    @lru_cache(maxsize=100)
    def preprocess_text(self, text: str) -> str:
        """Cached text preprocessing"""
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
        
        # Add periods after sentences that might be missing them for better TTS pacing
        text = re.sub(r'([a-z])\s+([A-Z])', r'\1. \2', text)
        
        # Normalize whitespace: collapse multiple newlines and spaces
        text = re.sub(r'\n\s*\n+', '\n', text).strip()
        text = re.sub(r'\s+', ' ', text)

        # Convert common abbreviations for better TTS reading
        abbreviations = {
            r'\be\.g\.\s': 'for example, ',
            r'\bi\.e\.\s': 'that is, ',
            r'\betc\.\s': 'etcetera. ',
            r'\bvs\.\s': 'versus ',
            r'\bFig\.\s': 'Figure ',
            r'\bfig\.\s': 'figure ',
        }
        for pattern, replacement in abbreviations.items():
            text = re.sub(pattern, replacement, text)

        return text
    
    def play_audio(self, audio_file):
        """
        Play an audio file of the user using the default system audio player.
        
        Args:
            audio_file: Path to the audio file to play
        """
        try:
            import platform
            import subprocess
            
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.run(['afplay', audio_file], check=True)
            elif system == 'Windows':
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME)
            else:  # Linux and others
                subprocess.run(['aplay', audio_file], check=True)
                
            logger.info(f"Played audio file: {audio_file}")
            return True
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False