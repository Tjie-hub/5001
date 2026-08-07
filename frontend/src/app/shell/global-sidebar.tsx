/**
 * Global Sidebar — Phase 9 Workstream B (B3).
 *
 * Zone A (Phase 4 P4-03 §3). Primary workspace navigation, and nothing else.
 *
 * Frozen constraints:
 *   P4-03 §3   MUST NEVER contain filters, charts, analysis, workspace actions
 *              or business commands
 *   P4-03 §4   order is fixed, with two separators
 *   P4-03 §5   one workspace per item; one icon; one label; active indicator;
 *              keyboard navigable. No nested workspace menus.
 *   P4-03 §17  no hidden navigation paths, no dynamic navigation
 *   NP-03      every workspace directly reachable
 *
 * Navigation is entirely static — it is read from the frozen registry, never
 * computed, filtered or reordered at runtime.
 */
import { useCallback, useRef, type KeyboardEvent } from 'react'
import { NavLink } from 'react-router'
import { WORKSPACE_GROUPS } from '../router/workspaces'
import { cx } from '@utils/cx'
import styles from './global-sidebar.module.css'

interface GlobalSidebarProps {
  /**
   * Called after navigating, so the mobile drawer can close itself.
   *
   * `| undefined` is explicit because `exactOptionalPropertyTypes` treats an
   * omitted property and an explicitly-undefined one as different types.
   */
  readonly onNavigate?: (() => void) | undefined
  readonly id?: string | undefined
}

export function GlobalSidebar({ onNavigate, id }: GlobalSidebarProps) {
  const navRef = useRef<HTMLElement>(null)

  /**
   * Arrow-key traversal (Phase 4 P4-03 §15, Phase 6 P6-43).
   *
   * Roving focus across the flat list of links; Home/End jump to the ends.
   * Tab order is untouched — this augments keyboard navigation rather than
   * replacing it, so there is no keyboard trap.
   */
  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLElement>) => {
    const keys = ['ArrowDown', 'ArrowUp', 'Home', 'End']
    if (!keys.includes(event.key)) return

    const links = Array.from(navRef.current?.querySelectorAll<HTMLAnchorElement>('a') ?? [])
    if (links.length === 0) return

    const currentIndex = links.findIndex((link) => link === document.activeElement)
    if (currentIndex === -1 && event.key !== 'Home' && event.key !== 'End') return

    event.preventDefault()

    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? links.length - 1
          : event.key === 'ArrowDown'
            ? (currentIndex + 1) % links.length
            : (currentIndex - 1 + links.length) % links.length

    links[nextIndex]?.focus()
  }, [])

  return (
    <nav
      id={id}
      ref={navRef}
      className={cx(styles['sidebar'])}
      aria-label="Workspaces"
      onKeyDown={handleKeyDown}
    >
      {WORKSPACE_GROUPS.map((group, groupIndex) => (
        <ul key={group[0]?.id ?? groupIndex} className={cx(styles['group'])}>
          {group.map((workspace) => (
            <li key={workspace.id}>
              <NavLink to={workspace.navPath} className={cx(styles['link'])} onClick={onNavigate}>
                {/* Placeholder marker. Iconography is Phase 6 P6-13 and belongs
                    to Workstream C; a text marker keeps the slot without
                    pre-empting the icon system. */}
                <span className={cx(styles['marker'])} aria-hidden="true">
                  ▸
                </span>
                <span>{workspace.label}</span>
                <span className={cx(styles['responsibility'])}>{workspace.responsibility}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      ))}
    </nav>
  )
}
