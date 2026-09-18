import asyncio
import os
import io
import soundfile as sf
import librosa
from gtts import gTTS

os.environ["LOCAL_STT_MODEL"] = "tiny"

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'packages', 'ai-gateway'))

from praxis_ai_gateway.transcription.local_faster_whisper import FasterWhisperTranscriber

sentences = [
    ("Technical Jargon", "I used XGBoost with early stopping on a held-out validation set to prevent overfitting."),
    ("Filler Words", "So, um, basically, I just, like, thought we could, you know, optimize the pipeline a bit."),
    ("Hinglish", "Bhai, production database migrate karna hai, please jaldi script likh de."),
    ("Fast/Mumbled", "Gotta get this done before the deadline otherwise the manager is gonna be really mad."),
    ("Low Volume / Accented", "The architecture utilizes microservices connected via an event bus.")
]

def synthesize_audio(text, lang='en', tld='com'):
    # gTTS generates MP3
    tts = gTTS(text, lang=lang, tld=tld)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    
    # Need to convert to 16kHz int16 PCM bytes
    # Librosa can read from BytesIO with soundfile backend? No, librosa uses soundfile which needs a real file or file-like object.
    # Write to a temp file
    temp_mp3 = "temp.mp3"
    with open(temp_mp3, "wb") as f:
        f.write(mp3_fp.read())
        
    y, sr = librosa.load(temp_mp3, sr=16000)
    # Convert to int16 bytes
    pcm_data = (y * 32767).astype('int16').tobytes()
    os.remove(temp_mp3)
    return pcm_data

async def main():
    print("Loading Local Transcriber...")
    transcriber = FasterWhisperTranscriber()
    await transcriber.connect({"language": None})
    
    # We must explicitly initialize _model via the background thread hack we added, or just wait.
    await asyncio.sleep(2) 
    
    print("\n--- Speech-to-Text Accuracy Test ---")
    
    for name, text in sentences:
        print(f"\n[Scenario: {name}]")
        print(f"Original Text : {text}")
        
        lang = 'hi' if 'Hinglish' in name else 'en'
        tld = 'co.in' if 'Hinglish' in name else 'com'
        
        pcm_data = synthesize_audio(text, lang=lang, tld=tld)
        
        # We simulate the RealtimeTranscriber interface
        await transcriber.send_audio(pcm_data)
        await transcriber.signal_segment_end()
        
        # Wait for the event
        result = await transcriber.queue.get()
        print(f"Transcribed   : {result['text']}")
        print(f"Detected Lang : {result['language']} (Conf: {result['confidence']:.2f})")

if __name__ == "__main__":
    asyncio.run(main())
