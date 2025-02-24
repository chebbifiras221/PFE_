import speech_recognition as sr
import pyttsx3
from datetime import datetime
import os

class SpeechProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()           # Initialize speech recognition
        self.engine = pyttsx3.init()                # Initialize text-to-speech engine
        self.audio_dir = "audio_history"            # The Directory to save audio files
        os.makedirs(self.audio_dir, exist_ok=True)  # Create directory if it doesn't exist

    def speech_to_text(self):
        self.listening = True       # Indicates whether the chatbot is currently listening
        try:
            # Create a microphone object to capture audio
            with sr.Microphone() as source:
                # Print a message to the user(in the terminal), indicating that the ai is listening
                print("Listening...")
                # Adjust the microphone sensitivity to the ambient noise level
                self.recognizer.adjust_for_ambient_noise(source)
                # Record audio from the microphone
                audio = self.recognizer.listen(source)
            # Attempt to recognize the speech
            return self.recognizer.recognize_google(audio)
        except sr.WaitTimeoutError:
            # If there is a wait timeout error, return None
            return None
        except Exception as e:
            # If there is an unexpected error, print its message and return 'None'
            print(f"Speech error: {str(e)}")
            return None
        except sr.UnknownValueError:
            # If the speech is unknown, return a sorry message
            return "Sorry, I couldn't understand that."
        except sr.RequestError:
            # If there is a request error, return another sorry message
            return "Could not request results. Check your internet connection."
        finally:
            # After the speech recognition attempt, set listening back to False
            self.listening = False

    def text_to_speech(self, text):
        """Basically, Saves each response with unique timestamp(day and time)"""
        # Get the current datetime and format it as a string
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create the filename by combining the timestamp and the filename prefix
        filename = os.path.join(self.audio_dir, f"response_{timestamp}.mp3")
        # Save the text-to-speech output to a file using the filename
        self.engine.save_to_file(text, filename)
        # Run the text-to-speech engine to generate the audio
        self.engine.runAndWait()
        # Return the filename of the saved audio
        return filename

    def cleanup(self):
        # Reset speech components
        self.engine.stop()