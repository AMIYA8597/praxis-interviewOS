import struct
import time

def test_audio_frame_header_unpack():
    # Header format: >BBIdI (18 bytes)
    proto_ver = 1
    frame_type = 1
    client_seq = 42
    capture_ts = 1700000000.123
    pcm_payload = b"\x00\x01\x02\x03" * 100  # 400 bytes (even)
    payload_len = len(pcm_payload)
    
    header = struct.pack(">BBIdI", proto_ver, frame_type, client_seq, capture_ts, payload_len)
    assert len(header) == 18
    
    unpacked = struct.unpack(">BBIdI", header)
    assert unpacked[0] == 1
    assert unpacked[1] == 1
    assert unpacked[2] == 42
    assert abs(unpacked[3] - capture_ts) < 1e-4
    assert unpacked[4] == 400

def test_audio_validation_rules():
    # Helper to validate frame processing logic
    def validate_frame(raw_bytes: bytes, last_client_seq: int | None):
        if len(raw_bytes) < 18:
            return False, "malformed_audio_frame", "Binary frame is too small for header", last_client_seq
        proto_ver, frame_type, client_seq, capture_ts, payload_len = struct.unpack(">BBIdI", raw_bytes[:18])
        if proto_ver != 1:
            return False, "unsupported_protocol", "Unsupported protocol version", last_client_seq
        if frame_type != 1:
            return False, "invalid_frame_type", "Invalid frame_type", last_client_seq
        if last_client_seq is not None and client_seq <= last_client_seq:
            return False, "out_of_order_sequence", "Duplicate or out-of-order sequence", last_client_seq
        if payload_len > 1024 * 1024:
            return False, "oversized_frame", "Payload exceeds max size", last_client_seq
        pcm = raw_bytes[18:]
        if len(pcm) != payload_len:
            return False, "malformed_audio_frame", "Payload length mismatch", last_client_seq
        if len(pcm) % 2 != 0:
            return False, "malformed_audio_frame", "PCM16 payload must be even bytes", last_client_seq
        return True, "ok", "", client_seq

    # 1. Valid frame
    pcm = b"\x01\x02" * 160
    hdr = struct.pack(">BBIdI", 1, 1, 0, time.time(), len(pcm))
    ok, err, msg, next_seq = validate_frame(hdr + pcm, None)
    assert ok is True
    assert next_seq == 0

    # 2. Reject invalid frame_type
    hdr_bad_type = struct.pack(">BBIdI", 1, 2, 1, time.time(), len(pcm))
    ok, err, msg, _ = validate_frame(hdr_bad_type + pcm, 0)
    assert ok is False
    assert err == "invalid_frame_type"

    # 3. Reject duplicate client_seq
    hdr_dup_seq = struct.pack(">BBIdI", 1, 1, 0, time.time(), len(pcm))
    ok, err, msg, _ = validate_frame(hdr_dup_seq + pcm, 0)
    assert ok is False
    assert err == "out_of_order_sequence"

    # 4. Reject out-of-order client_seq (e.g. sequence 2 followed by 1)
    hdr_lower_seq = struct.pack(">BBIdI", 1, 1, 1, time.time(), len(pcm))
    ok, err, msg, _ = validate_frame(hdr_lower_seq + pcm, 2)
    assert ok is False
    assert err == "out_of_order_sequence"

    # 5. Reject odd-length PCM16
    odd_pcm = b"\x01\x02\x03"  # 3 bytes
    hdr_odd = struct.pack(">BBIdI", 1, 1, 1, time.time(), len(odd_pcm))
    ok, err, msg, _ = validate_frame(hdr_odd + odd_pcm, 0)
    assert ok is False
    assert err == "malformed_audio_frame"
    assert "even" in msg
