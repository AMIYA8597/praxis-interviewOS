import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Table } from '../src/components/Table';

describe('Table', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<Table />);
    expect(getByTestId('table')).toBeInTheDocument();
  });
});
