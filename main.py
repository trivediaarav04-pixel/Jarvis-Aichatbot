"""Entry point for the Jarvis voice assistant.

python main.py          -> opens the HUD window
python main.py --cli    -> terminal-only mode
"""
import sys


def main():
    if "--cli" in sys.argv:
        from assistant import JarvisAssistant
        JarvisAssistant().run()
    else:
        from gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
