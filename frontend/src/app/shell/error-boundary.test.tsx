/**
 * Global error boundary contract — Phase 9 Workstream B (B9).
 *
 * Authority:
 *   Phase 7 v1.1 §16  a global Error Boundary sits at the top of the tree
 *   ADR-003 §11.3     it catches RENDER failures only
 *   Phase 4 NP-07     every screen provides a recovery path
 *   Phase 6 P6-31     no stack traces, no implementation detail
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppErrorBoundary } from './error-boundary'

function Exploding(): never {
  throw new Error('deliberate render failure')
}

/** React logs caught errors to console.error; silence it for these tests. */
function withSilencedConsole(run: () => void) {
  const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
  try {
    run()
  } finally {
    spy.mockRestore()
  }
}

describe('Phase 7 v1.1 §16 — global error boundary', () => {
  it('renders children when nothing throws', () => {
    render(
      <AppErrorBoundary>
        <p>healthy</p>
      </AppErrorBoundary>,
    )

    expect(screen.getByText('healthy')).toBeInTheDocument()
  })

  it('catches a render failure instead of unmounting the application', () => {
    withSilencedConsole(() => {
      render(
        <AppErrorBoundary>
          <Exploding />
        </AppErrorBoundary>,
      )
    })

    expect(screen.getByRole('heading', { level: 1, name: /something went wrong/i })).toBeVisible()
  })

  it('reports the error so observability can consume it (Workstream E)', () => {
    const onError = vi.fn()

    withSilencedConsole(() => {
      render(
        <AppErrorBoundary onError={onError}>
          <Exploding />
        </AppErrorBoundary>,
      )
    })

    expect(onError).toHaveBeenCalledOnce()
    expect(onError.mock.calls[0]?.[0]).toBeInstanceOf(Error)
  })
})

describe('Phase 4 NP-07 / Phase 6 P6-31 — recovery and messaging', () => {
  it('offers recovery paths and is never a dead end', () => {
    withSilencedConsole(() => {
      render(
        <AppErrorBoundary>
          <Exploding />
        </AppErrorBoundary>,
      )
    })

    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /return home/i })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: /search/i })).toHaveAttribute('href', '/search')
  })

  it('announces itself to assistive technology', () => {
    withSilencedConsole(() => {
      render(
        <AppErrorBoundary>
          <Exploding />
        </AppErrorBoundary>,
      )
    })

    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('never exposes the underlying error message or a stack trace', () => {
    withSilencedConsole(() => {
      render(
        <AppErrorBoundary>
          <Exploding />
        </AppErrorBoundary>,
      )
    })

    expect(document.body.textContent).not.toContain('deliberate render failure')
    expect(document.body.textContent).not.toMatch(/\bat\s+\w+\s+\(/)
  })

  it('recovers when the user retries', async () => {
    const user = userEvent.setup()
    let shouldThrow = true

    function Flaky() {
      if (shouldThrow) throw new Error('deliberate render failure')
      return <p>recovered</p>
    }

    withSilencedConsole(() => {
      render(
        <AppErrorBoundary>
          <Flaky />
        </AppErrorBoundary>,
      )
    })

    shouldThrow = false
    await user.click(screen.getByRole('button', { name: /try again/i }))

    expect(screen.getByText('recovered')).toBeInTheDocument()
  })
})
