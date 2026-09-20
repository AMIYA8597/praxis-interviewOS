import React from 'react';
export const ErrorState = ({ title = 'Error', message, suggestion }: { title?: string, message: string, suggestion?: string }) => (
  <div className="mb-4 p-4 bg-red-900 text-red-100 rounded border border-red-800">
    <h3 className="font-bold">{title}</h3>
    <p>{message}</p>
    {suggestion && <p className="text-sm mt-2 opacity-80">{suggestion}</p>}
  </div>
);
