import { useAudioFrameStream } from '../../src/renderer/hooks/useAudioFrameStream';
import { renderHook } from '@testing-library/react';

describe('useAudioFrameStream byte order', () => {
  it('encodes header fields in network byte order (big-endian) to match Python struct "!IdI"', () => {
    const mockWs = {
      readyState: 1,
      send: jest.fn()
    } as unknown as WebSocket;

    const { result } = renderHook(() => useAudioFrameStream('test', mockWs));

    // Send a 1-sample array so it's predictable
    const data = new Float32Array([0.5]);

    // Override Date.now temporarily so we can test a known timestamp
    const realDateNow = Date.now.bind(global.Date);
    global.Date.now = () => 1600000000000; // 1.6 billion seconds since epoch * 1000

    try {
      result.current.sendAudioFrame(data);

      // Implementation sends one combined frame (header + payload)
      expect(mockWs.send).toHaveBeenCalledTimes(1);
      const frame = (mockWs.send as jest.Mock).mock.calls[0][0] as ArrayBuffer;
      const view = new DataView(frame);

      // Frame layout:
      //   byte 0:    protocol version (1)
      //   byte 1:    frame type (1 = AUDIO_FRAME)
      //   bytes 2-5: sequence (uint32, big-endian)
      //   bytes 6-13: timestamp (float64, big-endian)
      //   bytes 14-17: payload length (uint32, big-endian)
      //   bytes 18+: PCM16 payload
      expect(view.getUint8(0)).toBe(1); // version
      expect(view.getUint8(1)).toBe(1); // frame type

      const seq = view.getUint32(2, false); // BIG ENDIAN
      const ts = view.getFloat64(6, false); // BIG ENDIAN
      const len = view.getUint32(14, false); // BIG ENDIAN

      expect(seq).toBe(0);
      expect(ts).toBe(1600000000);
      expect(len).toBe(2); // 1 float32 sample converted to 1 Int16 sample = 2 bytes
    } finally {
      global.Date.now = realDateNow;
    }
  });
});
