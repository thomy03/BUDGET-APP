// Jest DOM types extension for TypeScript
import '@testing-library/jest-dom'

declare global {
  namespace jest {
    interface Matchers<R> {
      toBeInTheDocument(): R
      toHaveClass(className: string): R
      toHaveValue(value: string | number | readonly string[]): R
      toBeChecked(): R
      toBeDisabled(): R
      toBeEnabled(): R
      toHaveAttribute(name: string, value?: string): R
      toHaveTextContent(text: string | RegExp): R
      toBeVisible(): R
      toHaveStyle(css: Record<string, any>): R
      toHaveDisplayValue(value: string | RegExp | readonly (string | RegExp)[]): R
    }
  }
}