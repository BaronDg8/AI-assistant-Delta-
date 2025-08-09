import sys
import time
import speech_recognition as sr
import pyttsx3
import os

def capture_voice_input():
    """Capture voice input from the microphone."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for activation command...")
        audio = recognizer.listen(source)
    return audio

def process_voice_command(text):
    """
    Check if the wake word 'cortana' appears in the converted text.
    Returns True if it does.
    """
    if "cortana" in text.lower():
        print("Starting")
        return True
    return False

def main():
    file_path = os.path.join(os.path.dirname(__file__), "Delta.py")
    
    # Loop continuously until the activation word is heard.
    while True:
        audio = capture_voice_input()
        recognizer = sr.Recognizer()
        try:
            text = recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            continue
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            continue

        if process_voice_command(text):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
                # Execute the contents of raphael.py in the current global namespace.
                exec(code, globals())
            except FileNotFoundError:
                print(f"File not found: {file_path}")
            break  # Once activated, exit the loop.
        else:
            print("Activation command not recognized. Listening again...\n")
        time.sleep(1)  # Optionally add a short delay before listening again.

if __name__ == "__main__":
    main()