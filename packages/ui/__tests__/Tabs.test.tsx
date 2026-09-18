import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Tabs } from '../src/components/Tabs';

describe('Tabs', () => {
  it('renders without crashing', () => {
    const { getByTestId } = render(<Tabs />);
    expect(getByTestId('tabs')).toBeInTheDocument();
  });
});
