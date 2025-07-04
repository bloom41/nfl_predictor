// Test setup following CLAUDE.md guidelines
// This file configures the testing environment for behavior-driven testing

import { jest } from '@jest/globals';

// Configure Jest timeouts
jest.setTimeout(10000);

// Mock external services by default (when they exist)
// jest.mock('../services/ml-service');
// jest.mock('../services/cache-service');

// Global test utilities
global.beforeEach(() => {
  // Reset all mocks before each test
  jest.clearAllMocks();
  
  // Reset any global state if needed
  process.env.NODE_ENV = 'test';
});

// Suppress console logs during tests unless explicitly needed
global.beforeAll(() => {
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'warn').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});
});

global.afterAll(() => {
  jest.restoreAllMocks();
});