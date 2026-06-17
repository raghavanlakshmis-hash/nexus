from tools.elevenlabs_stt import transcribe_audio
from dotenv import load_dotenv
load_dotenv()

with open("data/test_audio.wav", "rb") as f:
    audio_bytes = f.read()

result = transcribe_audio(audio_bytes)
print("Success:", result["success"])
print("Transcript:", result["transcript"])
print("Error:", result["error"])
