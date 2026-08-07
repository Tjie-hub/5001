/**
 * Global error boundary — Phase 9 Workstream B (B9).
 *
 * Phase 7 v1.1 §16 places a global Error Boundary at the top of the tree.
 * ADR-003 §11.3 is precise about its remit:
 *
 *   "Error Boundaries catch RENDER failures only. Data failures never reach an
 *    Error Boundary — they are values, handled by the owning component."
 *
 * So this catches component crashes. It must never become the destination for
 * failed requests; that is the workspace's five frozen error states
 * (NETWORK_ERROR, API_ERROR, PARTIAL_DATA, STALE_DATA, UNAUTHORIZED).
 *
 * It sits OUTSIDE the router (ADR-003 §16.1), which is why recovery uses plain
 * anchors rather than router links — if the router itself is what crashed, a
 * router-dependent escape hatch would crash with it.
 *
 * Phase 4 NP-07 and P4-14 §11: every error provides a recovery path, and
 * Phase 6 P6-31 forbids exposing stack traces or implementation detail.
 */
import { Component, type ErrorInfo, type ReactNode } from 'react'
import { cx } from '@utils/cx'
import styles from './error-boundary.module.css'

interface ErrorBoundaryProps {
  readonly children: ReactNode
  /** Test seam — lets a test assert the reporting hook fires. */
  readonly onError?: (error: Error, info: ErrorInfo) => void
}

interface ErrorBoundaryState {
  readonly hasError: boolean
}

export class AppErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // Observability wiring is Workstream E (task E5). Until then the error is
    // logged rather than swallowed — a silent boundary is worse than none.
    this.props.onError?.(error, info)
    console.error('[shell] unhandled render error', error, info.componentStack)
  }

  private readonly handleRetry = () => {
    this.setState({ hasError: false })
  }

  override render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <main className={cx(styles['container'])} role="alert">
        <h1 className={cx(styles['title'])}>Something went wrong</h1>

        {/* Phase 6 P6-31: explain the consequence, recommend an action, and
            never surface implementation detail. */}
        <p className={cx(styles['message'])}>
          The application could not display this screen. Your data has not been changed.
        </p>

        <div className={cx(styles['actions'])}>
          <button type="button" className={cx(styles['action'])} onClick={this.handleRetry}>
            Try again
          </button>
          <a className={cx(styles['action'])} href="/">
            Return home
          </a>
          <a className={cx(styles['action'])} href="/search">
            Search
          </a>
        </div>
      </main>
    )
  }
}
