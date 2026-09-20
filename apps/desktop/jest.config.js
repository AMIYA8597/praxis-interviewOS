const path = require('path');
const reactDir = path.dirname(require.resolve('react/package.json'));
const reactDomDir = path.dirname(require.resolve('react-dom/package.json'));

/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.json' }],
  },
  moduleNameMapper: {
    '^react$': require.resolve('react'),
    '^react/(.*)$': `${reactDir}/$1`,
    '^react-dom$': require.resolve('react-dom'),
    '^react-dom/(.*)$': `${reactDomDir}/$1`,
  }
};
