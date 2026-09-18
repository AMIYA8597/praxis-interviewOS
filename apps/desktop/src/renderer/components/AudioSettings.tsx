import React, { useEffect, useState } from 'react';

export function AudioSettings() {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('default');
  
  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then(deviceInfos => {
      const audioInputs = deviceInfos.filter(d => d.kind === 'audioinput');
      setDevices(audioInputs);
    });
  }, []);
  
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">Microphone</label>
      <select
        value={selectedDevice}
        onChange={(e) => setSelectedDevice(e.target.value)}
        className="w-full bg-gray-800 text-white rounded p-2"
      >
        {devices.map(d => (
          <option key={d.deviceId} value={d.deviceId}>{d.label || `Microphone ${d.deviceId}`}</option>
        ))}
      </select>
    </div>
  );
}
