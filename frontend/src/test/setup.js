import '@testing-library/jest-dom'
import { setupServer } from 'msw/node'
import { handlers } from './mocks/handlers'

export const server = setupServer(...handlers)

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'warn' });
  // Mock window.scrollTo since jsdom does not implement it
  global.window.scrollTo = () => {};
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

