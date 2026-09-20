import pytest
import asyncio
from unittest.mock import patch, MagicMock

from realtime_agent.app.audio.tts import PiperTTSAdapter
from praxis_ai_gateway.cancellation import CancellationToken

@pytest.mark.asyncio
async def test_tts_cancellation():
    token = CancellationToken()
    
    # We will feed a stream of tokens that forms 3 sentences
    async def text_stream():
        tokens = [
            "This is the first sentence. ",
            "This is the second ",
            "sentence. ",
            "And this is the third sentence. "
        ]
        for idx, t in enumerate(tokens):
            yield t
            await asyncio.sleep(0.01)
            # Cancel during the second sentence
            if idx == 1:
                token.cancel(reason="test")
                
    mock_voice = MagicMock()
    # mock_voice.synthesize returns a list of mock audio chunks
    def mock_synthesize(text):
        mock_chunk = MagicMock()
        mock_chunk.audio_int16_bytes = b'fake_audio'
        return [mock_chunk]
        
    mock_voice.synthesize.side_effect = mock_synthesize

    with patch('realtime_agent.app.audio.tts.os.path.exists', return_value=True), \
         patch('realtime_agent.app.audio.tts.PiperVoice', create=True) as mock_piper_cls:
        
        mock_piper_cls.load.return_value = mock_voice
        # Also mock _get_piper_voice to return our mock voice
        with patch('realtime_agent.app.audio.tts._get_piper_voice', return_value=mock_voice):
            adapter = PiperTTSAdapter(voice_model="fake.onnx")
            
            yielded_chunks = []
            async for chunk in adapter.synthesize_streaming(text_stream(), token):
                yielded_chunks.append(chunk)
                
            # It should yield for the first sentence, but abort during/before the second or third sentence
            # because token is cancelled mid-way through the second sentence chunks.
            assert len(yielded_chunks) >= 1
            # Verify we didn't synthesize the 3rd sentence
            # It should only call synthesize for the first sentence
            called_texts = [call[0][0] for call in mock_voice.synthesize.call_args_list]
            assert "This is the first sentence." in called_texts
            assert "And this is the third sentence." not in called_texts
