/** Plain-language copy for Trust tab info tooltips (matches backend notary formula). */
export const TRUST_SCORE_INFO =
  'Trust Score (0–100) blends four signals from your tenant: 40% adversary test pass rate, 20% gate health (requests not held for review), 20% block health (requests not blocked), and 20% evidence ledger integrity (hash chain valid). Bands: ≥85 CERTIFIED, ≥65 CONDITIONAL, below AT_RISK. Updates as new sessions are processed.';

export const CONTROL_COVERAGE_INFO =
  'Count of mapped controls in the Aegis Librarian library per framework (NIST AI RMF, ISO 27001, EU AI Act). Higher coverage means more regulatory controls are wired into automated checks.';

export const ADVERSARY_COVERAGE_INFO =
  'Results from continuous red-team probes (injection, jailbreak, logic abuse) run against gateway traffic. Pass rate feeds directly into the Trust Score (40% weight).';
