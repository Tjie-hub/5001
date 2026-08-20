/**
 * ADR-003 §11.1: "ViewModel selects message + recovery actions" for the
 * error state the Domain Adapter already classified. Every state offers at
 * least one recovery path (S-11, NP-07).
 */
import type { WorkspaceErrorState } from '../adapters/error-classification'

export interface ErrorPresentation {
  readonly state: WorkspaceErrorState
  readonly title: string
  readonly message: string
  readonly recoveryActions: readonly ('retry' | 'goToDecisionCenter')[]
}

const PRESENTATIONS: Record<WorkspaceErrorState, Omit<ErrorPresentation, 'state'>> = {
  NETWORK_ERROR: {
    title: 'Connection problem',
    message: 'Could not reach the server. Check your connection and try again.',
    recoveryActions: ['retry'],
  },
  SEARCH_UNAVAILABLE: {
    title: 'Search unavailable',
    message: 'The search service could not be reached right now.',
    recoveryActions: ['retry', 'goToDecisionCenter'],
  },
  UNAUTHORIZED: {
    title: 'Not authorized',
    message: 'You are not authorized to search.',
    recoveryActions: ['goToDecisionCenter'],
  },
}

export function presentError(state: WorkspaceErrorState): ErrorPresentation {
  return { state, ...PRESENTATIONS[state] }
}
