import speech_recognition as sr
import pyttsx3

class SpeechProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()

    def speech_to_text(self):
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
        try:
            return self.recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Sorry, I couldn't understand that."
        except sr.RequestError:
            return "Could not request results. Check your internet connection."

    def text_to_speech(self, text):
        self.engine.say(text)
        self.engine.runAndWait()
