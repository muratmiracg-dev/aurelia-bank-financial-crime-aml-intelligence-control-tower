# Security policy

## Scope

This repository is an educational, synthetic-data decision-support demonstration. It must not receive production credentials, customer data, sanctions-list extracts containing personal data, investigation notes or regulatory submissions.

## Supported version

Security fixes are applied to the latest release on `main`.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when available. Do not open a public issue containing credentials, personal data or exploit details. Include the affected component, reproduction steps, impact and a proposed mitigation if known.

## Defensive defaults

- The API is read-only and supports an optional API key.
- Containers run with a read-only filesystem and `no-new-privileges` in Compose.
- Validation labels are separated from detection inputs.
- No STR/ŞİB submission or customer restriction can be automated by this codebase.
- GitHub Actions use least-privilege permissions; CodeQL scans Python changes.
