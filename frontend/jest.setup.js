// Jest setup for React Testing Library
import '@testing-library/jest-dom'

// Mock console methods to reduce noise in test output
global.console = {
  ...console,
  // Uncomment to silence console during tests
  // log: jest.fn(),
  // debug: jest.fn(),
  // info: jest.fn(),
  // warn: jest.fn(),
  // error: jest.fn(),
}

// Mock window.location (check if already defined)
if (!window.location) {
  Object.defineProperty(window, 'location', {
    value: {
      href: 'http://localhost:3000',
      pathname: '/',
      search: '',
      hash: '',
      assign: jest.fn(),
      reload: jest.fn(),
      replace: jest.fn(),
    },
    writable: true,
  })
}

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.sessionStorage = sessionStorageMock

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor(cb) {
    this.cb = cb
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor(cb) {
    this.cb = cb
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}