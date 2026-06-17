from pydub import AudioSegment

# Replace this with your actual recording filename
input_file = r"C:\Users\laksh\Documents\MasteringGenAI\week3\nexus\data\test_audio.m4a"

audio = AudioSegment.from_file(input_file)
audio.export("test_audio.wav", format="wav")
print("Done — test_audio.wav created")
