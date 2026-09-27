/** PC-012: the version of the Terms and Privacy Policy a new account accepts. The control plane
 * records the same value (OMNISTACKAI_TERMS_VERSION) against each account at sign-up. */
export function termsVersion(): string {
  return process.env.OMNISTACKAI_TERMS_VERSION ?? "2026-09-27";
}
