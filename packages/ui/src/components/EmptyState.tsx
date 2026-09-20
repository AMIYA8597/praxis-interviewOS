import React from 'react';
export const EmptyState = ({ message }: { message: string }) => (
  <div className="p-8 text-center text-gray-500 border border-dashed border-gray-700 rounded bg-gray-900">
    {message}
  </div>
);
