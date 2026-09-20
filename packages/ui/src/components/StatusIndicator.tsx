import React from 'react';
export const StatusIndicator = ({ status }: { status: 'online' | 'offline' | 'busy' }) => {
  const colors = { online: 'bg-green-500', offline: 'bg-red-500', busy: 'bg-yellow-500' };
  return <div className={`w-3 h-3 rounded-full ${colors[status]}`}></div>;
};
