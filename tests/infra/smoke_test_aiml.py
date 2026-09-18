import os
import time
import numpy as np
import soundfile as sf
import warnings
warnings.filterwarnings("ignore")

def generate_sample_audio(filename="sample.wav", duration=3.0, sample_rate=16000):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate some varying frequencies to make it "sound" like something
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) * np.exp(-t)
    sf.write(filename, audio, sample_rate)
    return filename

def test_faster_whisper(audio_file):
    print("\n--- Testing faster-whisper ---")
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_file, beam_size=5)
    text = ""
    for segment in segments:
        text += segment.text + " "
    print(f"Transcription: '{text.strip()}'")
    print("faster-whisper test passed.")

def test_silero_vad(audio_file):
    print("\n--- Testing silero-vad ---")
    import torch
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                  model='silero_vad',
                                  force_reload=False,
                                  onnx=True, trust_repo=True)
    
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
    wav = read_audio(audio_file, sampling_rate=16000)
    speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)
    print(f"Detected speech segments: {speech_timestamps}")
    print("silero-vad test passed.")

def test_piper_tts():
    print("\n--- Testing Piper TTS ---")
    import subprocess
    model_path = "piper_model.onnx"
    output_wav = "piper_output.wav"
    text = "Hello, this is a test of Piper TTS."
    
    process = subprocess.Popen(["uv", "run", "piper", "--model", model_path, "--output_file", output_wav], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate(input=text.encode("utf-8"))
    
    if os.path.exists(output_wav):
        print("Piper output WAV created successfully.")
    else:
        print("Failed to create Piper WAV output.")
        print("Stderr:", stderr.decode('utf-8'))

def test_sentence_transformers():
    print("\n--- Testing sentence-transformers ---")
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    sentences = [
        "How do I install the software?",
        "What are the setup instructions for this application?",
        "I like to eat apples and bananas."
    ]
    embeddings = model.encode(sentences)
    dim = embeddings.shape[1]
    print(f"Embedding dimension: {dim} (Expected: 384)")
    assert dim == 384, "Dimension mismatch!"
    
    sim_related = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    sim_unrelated = cosine_similarity([embeddings[0]], [embeddings[2]])[0][0]
    print(f"Similarity (related): {sim_related:.4f}")
    print(f"Similarity (unrelated): {sim_unrelated:.4f}")
    assert sim_related > sim_unrelated, "Similarity check failed!"
    print("sentence-transformers test passed.")

if __name__ == "__main__":
    audio_file = generate_sample_audio()
    try:
        test_faster_whisper(audio_file)
    except Exception as e:
        print(f"faster-whisper failed: {e}")
        
    try:
        test_silero_vad(audio_file)
    except Exception as e:
        print(f"silero-vad failed: {e}")
        
    try:
        test_piper_tts()
    except Exception as e:
        print(f"piper-tts failed: {e}")
        
    try:
        test_sentence_transformers()
    except Exception as e:
        print(f"sentence-transformers failed: {e}")
