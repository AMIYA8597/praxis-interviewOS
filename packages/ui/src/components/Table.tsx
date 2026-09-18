import React from 'react';

export interface TableProps {
  children?: React.ReactNode;
  [key: string]: any;
}

export const Table: React.FC<TableProps> = ({ children, ...props }) => {
  return (
    <div data-testid="table" aria-label="Table" {...props}>
      {children}
    </div>
  );
};
