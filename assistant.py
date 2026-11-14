"""Coordinates speech, built-in commands, and the optional AI brain."""
from speech import SpeechEngine
from ai_brain import AIBrain
from commands import run_command
from config import APP_NAME

EXIT_PHRASES = {"exit", "quit", "stop listening", "goodbye", "shutdown jarvis"}


def _ignore(kind, text=None):
    pass


class JarvisAssistant:
    def __init__(self, on_event=_ignore):
        """on_event(kind, text) is called for "state", "user", "jarvis" and
        "system" events. The GUI uses it; the terminal version ignores it."""
        self.on_event = on_event
        self.voice = SpeechEngine(on_event=on_event)
        self.brain = AIBrain()

    def handle(self, text: str) -> bool:
        if not text:
            return True
        self.on_event("user", text)
        if text in EXIT_PHRASES:
            self.voice.speak("Goodbye. JARVIS shutting down.")
            return False

        self.on_event("state", "thinking")
        result = run_command(text)
        if result is not None:
            self.voice.speak(result)
            return True

        answer = self.brain.ask(text)
        self.voice.speak(answer)
        return True

    def startup(self):
        self.voice.speak(f"{APP_NAME} systems online.")
        if self.brain.enabled:
            self.voice.speak("AI connection is ready.")
        else:
            self.voice.speak("Built-in commands are ready. AI mode needs an API key.")
        self.voice.speak("Say a command. Say stop listening to exit.")

    def run(self):
        """Terminal loop (python main.py --cli)."""
        self.startup()
        running = True
        while running:
            try:
                spoken_text = self.voice.listen()
                running = self.handle(spoken_text)
            except KeyboardInterrupt:
                print("\nStopped by keyboard.")
                break
