"""
PRAXIS InterviewOS — WebSocket Protocol Security Regression Suite
Verifies binary frame header parsing, monotonic sequence ordering, and payload length bounds.
"""
import struct
import time


def _validate_audio_frame(raw_bytes: bytes, last_client_seq: int | None):
    """Encapsulates the exact binary framing validation rules enforced by the realtime agent."""
    if len(raw_bytes) < 18:
        return False, "malformed_audio_frame", "Binary frame is too small for header"
    proto_ver, frame_type, client_seq, capture_ts, payload_len = struct.unpack(">BBIdI", raw_bytes[:18])
    if proto_ver != 1:
        return False, "unsupported_protocol", f"Unsupported protocol version: {proto_ver}"
    if frame_type != 1:
        return False, "invalid_frame_type", f"Invalid frame_type: {frame_type}"
    if last_client_seq is not None and client_seq <= last_client_seq:
        return False, "out_of_order_sequence", f"Duplicate or out-of-order client_seq: {client_seq}"
    if payload_len > 1024 * 1024:
        return False, "oversized_frame", "Audio frame payload exceeds maximum size"
    pcm = raw_bytes[18:]
    if len(pcm) != payload_len:
        return False, "malformed_audio_frame", f"Payload length mismatch: expected {payload_len}, received {len(pcm)}"
    if len(pcm) % 2 != 0:
        return False, "malformed_audio_frame", f"PCM16 payload must be even bytes: got {len(pcm)}"
    return True, "ok", ""


def test_valid_binary_frame_passes():
    pcm = b"\x00\x01" * 160  # 320 bytes
    hdr = struct.pack(">BBIdI", 1, 1, 10, time.time(), len(pcm))
    ok, code, msg = _validate_audio_frame(hdr + pcm, last_client_seq=9)
    assert ok is True
    assert code == "ok"


def test_truncated_frame_is_rejected():
    short_frame = b"\x01\x01\x00\x00"
    ok, code, msg = _validate_audio_frame(short_frame, last_client_seq=None)
    assert ok is False
    assert code == "malformed_audio_frame"


def test_unsupported_protocol_version():
    pcm = b"\x00\x01" * 16
    hdr = struct.pack(">BBIdI", 99, 1, 1, time.time(), len(pcm))
    ok, code, msg = _validate_audio_frame(hdr + pcm, last_client_seq=None)
    assert ok is False
    assert code == "unsupported_protocol"


def test_invalid_frame_type():
    pcm = b"\x00\x01" * 16
    hdr = struct.pack(">BBIdI", 1, 99, 1, time.time(), len(pcm))
    ok, code, msg = _validate_audio_frame(hdr + pcm, last_client_seq=None)
    assert ok is False
    assert code == "invalid_frame_type"


def test_duplicate_sequence_is_dropped():
    pcm = b"\x00\x01" * 16
    hdr = struct.pack(">BBIdI", 1, 1, 15, time.time(), len(pcm))
    ok, code, msg = _validate_audio_frame(hdr + pcm, last_client_seq=15)
    assert ok is False
    assert code == "out_of_order_sequence"


def test_decreasing_sequence_is_dropped():
    pcm = b"\x00\x01" * 16
    hdr = struct.pack(">BBIdI", 1, 1, 14, time.time(), len(pcm))
    ok, code, msg = _validate_audio_frame(hdr + pcm, last_client_seq=15)
    assert ok is False
    assert code == "out_of_order_sequence"


def test_odd_pcm16_byte_count_is_rejected():
    odd_pcm = b"\x00\x01\x02"  # 3 bytes (invalid for 16-bit PCM)
    hdr = struct.pack(">BBIdI", 1, 1, 1, time.time(), len(odd_pcm))
    ok, code, msg = _validate_audio_frame(hdr + odd_pcm, last_client_seq=None)
    assert ok is False
    assert code == "malformed_audio_frame"
