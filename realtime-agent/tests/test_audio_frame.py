import struct
import pytest

def test_audio_frame_byte_order():
    # Matches the TS test: seq=0, ts=1600000000.0, len=2
    # Network byte order (big-endian)
    packed = struct.pack("!IdI", 0, 1600000000.0, 2)
    
    assert len(packed) == 16
    
    # sequence
    assert packed[0:4] == b'\x00\x00\x00\x00'
    
    # timestamp
    assert packed[4:12] == b'A\xd7\xd7\x84\x00\x00\x00\x00'
    
    # length
    assert packed[12:16] == b'\x00\x00\x00\x02'
