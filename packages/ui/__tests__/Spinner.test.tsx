import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Spinner } from '../src/components/Spinner';

describe('Spinner', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<Spinner />);
    expect(getByTestId('spinner')).toBeInTheDocument();
  });
});
