"""Optional LLM connection. The assistant still works without an API key."""
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

SYSTEM_INSTRUCTIONS = (
    "You are JARVIS, a friendly and concise Python voice assistant. "
    "Answer clearly in a way that sounds natural when spoken aloud. "
    "If you are unsure, say so. Do not claim to have performed computer actions."
)

class AIBrain:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.history = []

    @property
    def enabled(self):
        return self.client is not None

    def ask(self, question: str) -> str:
        if not self.client:
            return ("AI mode is not configured yet. Add your API key to the .env file, "
                    "or ask me to open a website, tell the time, or check the weather.")
        self.history.append({"role": "user", "content": question})
        # Keep a short conversation window to control token use.
        recent = self.history[-10:]
        try:
            response = self.client.responses.create(
                model=OPENAI_MODEL,
                instructions=SYSTEM_INSTRUCTIONS,
                input=recent,
                max_output_tokens=250,
            )
            answer = response.output_text.strip()
            self.history.append({"role": "assistant", "content": answer})
            return answer or "I didn't get a response. Please try again."
        except Exception as exc:
            # Avoid exposing secrets or long raw tracebacks to the user.
            print(f"AI request failed: {type(exc).__name__}: {exc}")
            return "I couldn't reach the AI service. Check your API key, internet connection, and account access."
