"""Speech input (STT) and speech output (TTS)."""
import speech_recognition as sr
import pyttsx3
from config import VOICE_RATE, VOICE_VOLUME, LISTEN_TIMEOUT, PHRASE_TIME_LIMIT


def _ignore(kind, text=None):
    pass


class SpeechEngine:
    def __init__(self, on_event=_ignore):
        self.on_event = on_event
        self.recognizer = sr.Recognizer()
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", VOICE_RATE)
        self.tts.setProperty("volume", VOICE_VOLUME)

    def speak(self, text: str) -> None:
        text = str(text).strip()
        if not text:
            return
        print(f"JARVIS: {text}")
        self.on_event("jarvis", text)
        self.on_event("state", "speaking")
        try:
            self.tts.say(text)
            self.tts.runAndWait()
        finally:
            self.on_event("state", "idle")

    def listen(self) -> str:
        """Listen once and return recognized text, or an empty string."""
        try:
            with sr.Microphone() as source:
                print("\nListening... (speak now)")
                self.on_event("state", "listening")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT,
                    phrase_time_limit=PHRASE_TIME_LIMIT,
                )
            self.on_event("state", "thinking")
            text = self.recognizer.recognize_google(audio, language="en-IN")
            print(f"YOU: {text}")
            return text.lower().strip()
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            print("I couldn't understand that. Please try again.")
            self.on_event("system", "I couldn't understand that. Please try again.")
            return ""
        except sr.RequestError as exc:
            print(f"Speech recognition service error: {exc}")
            self.speak("Speech recognition is unavailable. Check your internet connection.")
            return ""
        except (OSError, AttributeError) as exc:
            print(f"Microphone problem: {exc}")
            self.speak("I cannot access the microphone. Check your microphone and PyAudio installation.")
            return ""
        finally:
            self.on_event("state", "idle")
