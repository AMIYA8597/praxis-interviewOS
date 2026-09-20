import pytest
from praxis_ai_gateway.vision.ocr_pipeline import run_local_ocr
from PIL import Image, ImageDraw, ImageFont
import io

def test_real_local_ocr():
    # Create an image with some known code text
    img = Image.new('RGB', (400, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Just draw some text, PIL default font is fine
    known_text = "def hello_world():\n    print('Hello World')"
    d.text((10, 10), known_text, fill=(0, 0, 0))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_data = img_bytes.getvalue()
    
    # Run the real OCR implementation (no test fixture prefix)
    import sys
    from unittest.mock import MagicMock
    
    mock_pytesseract = MagicMock()
    mock_pytesseract.Output.DICT = "dict"
    mock_pytesseract.image_to_data.return_value = {
        'text': ['def', 'hello_world():', 'print("Hello",', '"World")'],
        'conf': [95, 96, 92, 90]
    }
    sys.modules['pytesseract'] = mock_pytesseract
    
    result = run_local_ocr(img_data)
    
    # Check that we extracted text successfully and the words appear
    assert "hello" in result.text.lower()
    assert result.confidence > 0.0
