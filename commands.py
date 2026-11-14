"""A small, explicit allow-list of local assistant actions."""
from datetime import datetime
import webbrowser
import requests
from config import WEATHER_DEFAULT_CITY

SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "stackoverflow": "https://stackoverflow.com",
}

def run_command(text: str):
    """Return a response string, or None if this is not a built-in command."""
    command = text.lower().strip()

    if command in {"what time is it", "tell me the time", "time"} or "what is the time" in command:
        return "The time is " + datetime.now().strftime("%I:%M %p")

    if command in {"what is today's date", "tell me the date", "date"} or "today's date" in command:
        return "Today is " + datetime.now().strftime("%A, %d %B %Y")

    for site, url in SITES.items():
        if command in {f"open {site}", f"launch {site}"}:
            webbrowser.open(url)
            return f"Opening {site}."

    if command.startswith("search for "):
        query = command.removeprefix("search for ").strip()
        if query:
            webbrowser.open("https://www.google.com/search?q=" + requests.utils.quote(query))
            return f"Searching the web for {query}."

    if "weather" in command:
        city = WEATHER_DEFAULT_CITY
        if "weather in " in command:
            city = command.split("weather in ", 1)[1].strip(" ?.")
        try:
            response = requests.get(f"https://wttr.in/{requests.utils.quote(city)}?format=3", timeout=8)
            response.raise_for_status()
            return "Here is the current weather: " + response.text.strip()
        except requests.RequestException:
            return "I couldn't retrieve the weather right now."

    return None
