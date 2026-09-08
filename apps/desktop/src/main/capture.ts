import { globalShortcut, desktopCapturer, ipcMain } from 'electron';

export function setupScreenshotCapture() {
  // Explicit, user-triggered single-shot capture. No continuous background recording.
  const registered = globalShortcut.register('CommandOrControl+Shift+S', async () => {
    try {
      console.log("User triggered explicit screen capture.");
      const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
      
      if (sources.length > 0) {
        // Grab the primary screen thumbnail as a NativeImage
        const imageBuffer = sources[0].thumbnail.toPNG();
        
        // Push buffer to the frontend to trigger the Study Workbench
        // In a real app, we'd send this over IPC to the active BrowserWindow
        // mainWindow.webContents.send('capture-ready', imageBuffer);
        console.log(`Captured ${imageBuffer.length} bytes.`);
      }
    } catch (e) {
      console.error("Capture failed:", e);
    }
  });

  if (!registered) {
    console.error("Failed to register global shortcut for capture.");
  }
}

export function cleanupScreenshotCapture() {
  globalShortcut.unregister('CommandOrControl+Shift+S');
}
