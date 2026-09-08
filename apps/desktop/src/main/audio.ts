import { desktopCapturer, ipcMain } from 'electron';

export function setupAudioCapture() {
  ipcMain.handle('enumerate-devices', async () => {
    // Note: To get raw hardware, we usually rely on the renderer's navigator.mediaDevices.
    // However, on Windows, system loopback requires desktopCapturer.
    try {
      const sources = await desktopCapturer.getSources({ types: ['audio'] });
      const hasLoopback = sources.some(s => s.id.startsWith('loopback'));
      return { hasLoopback, sources: sources.map(s => ({ id: s.id, name: s.name })) };
    } catch (e) {
      console.error("Failed to enumerate desktop audio:", e);
      return { hasLoopback: false, sources: [] };
    }
  });

  ipcMain.on('audio-frame', (event, pcmData: Uint8Array, sequence: number, captureTimestamp: number) => {
    // 1. We receive raw PCM from the secure renderer context via IPC.
    // 2. Here we could resample to 16kHz mono using fluent-ffmpeg or wavefile
    // 3. Forward to the Realtime Python Agent WebSocket
    
    // Stub: compute RMS for the live audio-level meter
    let sumSquares = 0;
    const view = new Int16Array(pcmData.buffer);
    for (let i = 0; i < view.length; i++) {
        sumSquares += view[i] * view[i];
    }
    const rms = Math.sqrt(sumSquares / view.length);
    
    // Push the RMS meter back to the UI at ~10Hz
    event.sender.send('audio-meter', rms);
  });
}
