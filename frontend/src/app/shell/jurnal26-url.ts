/**
 * jurnal26 app URL — shared by the freeze banner and the frozen workspace
 * page (frontend freeze, owner-directed 2026-10-06).
 *
 * The jurnal26 app serves on port 5004 of the SAME host that serves this
 * page, so the URL is built from window.location.hostname — no hardcoded IP,
 * works from localhost, the LAN address, or any future host. Kept in its own
 * module so components can stay pure component exports (react-refresh).
 */
export function jurnal26Url(): string {
  return `http://${window.location.hostname}:5004/`
}
