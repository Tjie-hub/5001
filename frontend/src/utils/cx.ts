/**
 * Class-name composition — Phase 9 Workstream B.
 *
 * Two problems, one helper.
 *
 * 1. Vite types CSS modules as Record<string, string>. Under the
 *    `noUncheckedIndexedAccess` we enabled in Workstream A, every lookup is
 *    `string | undefined`, which `exactOptionalPropertyTypes` then refuses to
 *    pass to props typed `string`. `cx` narrows once, here, instead of an
 *    `?? ''` at every call site.
 *
 * 2. Composing several classes with a template literal produces stray spaces
 *    when one is absent. Filtering handles it.
 *
 * Leaf utility: imports nothing, knows nothing about layers or domains.
 */
export function cx(...values: readonly (string | false | null | undefined)[]): string {
  return values.filter((value): value is string => Boolean(value)).join(' ')
}
