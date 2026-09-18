import React from 'react';
import { Button } from './Button';

export default {
  title: 'Components/Button',
  component: Button,
};

export const Default = () => <Button>Click me</Button>;
export const Primary = () => <Button variant="primary">Primary</Button>;
export const Disabled = () => <Button disabled>Disabled</Button>;
