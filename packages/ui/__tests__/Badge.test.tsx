import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Badge } from '../src/components/Badge';

describe('Badge', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<Badge />);
    expect(getByTestId('badge')).toBeInTheDocument();
  });
});
