# HealthUp Studio release: 30 substantial upgrades

The selected Organic Ascent logo, dark walnut, bamboo, ivory type, sage and aqua remain the brand foundation. Everything below has implementation, not placeholder pages. Account-dependent capabilities are intentionally disabled in the public static deployment until its real server, identity, transactional email and reviewed notices are configured.

| # | Upgrade | Where / behavior |
| --- | --- | --- |
| 1 | Duration-adaptive wellness studio | 1/2/3/5/10/15/20/30 minutes produce exact-duration instructions and a matching countdown. |
| 2 | Category-based practice selection | Mindfulness, self-care, movement, hydration, mindful food, wind-down, or surprise. |
| 3 | Recency-aware random activities | Recent distinct activities are avoided within available category choices. |
| 4 | Immediate activity timer popup | Starting in Today, Studio or Mind opens the active guide and countdown. |
| 5 | Live duration editing | Editing the selected active practice changes its name, stages and clock together. |
| 6 | Resilient pause/resume/restart | Elapsed-clock timing survives navigation/refresh and avoids counting interval ticks. |
| 7 | Timed calendar routines | Plans can launch a timer using the actual saved event duration. |
| 8 | Non-repeating affirmation rotation | Per-category history avoids repeats until cycling through available messages. |
| 9 | Optional automatic thought rotation | Visible Mind view changes thoughts every minute; quiet mode disables this. |
| 10 | Gentle return-day widget | Recent activity days and lifetime returns stay distinct; a missed day erases nothing. |
| 11 | Post-login check-in | Each fresh sign-in presents the question; answering or “Prefer not to say” continues. |
| 12 | Custom daily check-in popup | User-selected time, while open; quiet mode and opt-out are honored. |
| 13 | Local mood-based guide recommendations | Transparent topic rules, not diagnoses, risk scoring or remote AI processing. |
| 14 | Personalization controls | Disable suggestions and use a general selection without losing core tools. |
| 15 | Journal creation/edit/history | Dated entries with private-device persistence. |
| 16 | Dream book | Dedicated original prompts without AI interpretation or clinical claims. |
| 17 | Gratitude entries | Optional, grounded prompts without forced positivity. |
| 18 | Journal search/tags/favorites | Search words, titles and tags; edit, favorite, export and confirm deletion. |
| 19 | Encrypted device storage | AES-GCM records and non-extractable browser-held keys; legacy records migrate on save. |
| 20 | Passphrase-protected backups | AES-256-GCM/PBKDF2 encrypted export/import; wrong passwords fail safely. |
| 21 | Account-isolated device stores | Separate namespaces/keys avoid normal UI exposure between accounts on one browser. |
| 22 | Verified adult accounts | Server-side registration, Argon2id passwords, eligibility and email verification. |
| 23 | Secure password recovery | Expiring, hashed, single-use email tokens; reset revokes existing sessions. |
| 24 | Secure sessions and revocation | HttpOnly/Secure/Strict cookies, Origin/CSRF checks and sign-out across devices. |
| 25 | Versioned acknowledgement receipts | Required essential account consent is separate from optional cloud sharing; updated notices can require re-acknowledgement. |
| 26 | Optional encrypted cloud backup | Server encryption, explicit opt-in, withdrawal deletion, authenticated export and account deletion. |
| 27 | Regional privacy/rights center | Short expandable policies, downloadable receipts, official laws and privacy request/appeal flow. |
| 28 | Staff dashboard with MFA | Server roles, TOTP replay checks, short staff authorization, privacy queue and non-sensitive audit overview. No private wellness-entry browser. |
| 29 | Real subscription boundaries | Free core and Plus backup; configured Stripe price, explicit renewal acknowledgement, signed webhooks, server entitlements and cancellation portal. No fake checkout. |
| 30 | Visual and connectivity revamp | Eight realistic no-people wellness scenes, self-hosted fonts, animated progress, reduced-motion behavior, connection fallback, optional calorie logging and global support directory. |

Tests include ordinary wellness workflows, encrypted persistence/offline startup, adaptive timers, non-repeating content, journal operations, account verification/login/check-in/isolation, consent boundaries, resets, staff roles/MFA, and subscription webhook security.

This release is not a claim of HIPAA certification, worldwide compliance, independent penetration testing, or clinical efficacy. See COMPLIANCE.md and DEPLOYMENT.md for the remaining production requirements.
