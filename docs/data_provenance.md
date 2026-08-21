# Data provenance and source register

Data classes are intentionally separated. No public source is presented as an Aurelia Bank record.

| Data class | Content | Use | Location |
|---|---|---|---|
| Controlled synthetic | Customers, accounts, transactions and relationships | Demonstration analytics | `data/demo` |
| Synthetic validation truth | Injected scenario labels | Post-detection validation only | `data/demo/typology_truth.csv` |
| Synthetic internal taxonomy | Fictitious jurisdiction `XH` and illustrative risk tiers | Scenario testing | `data/reference/jurisdiction_risk.csv` |
| Official public methodology | AML/CFT obligations, risk-based approach and payment transparency | Governance context | Links below |
| Derived analytics | KYC, rules, anomaly, graph, alerts, cases and controls | Decision support | `artifacts/results` |

## Primary official references

Accessed 21 August 2026.

- [MASAK sectoral suspicious transaction reporting guides](https://masak.hmb.gov.tr/sektorel-sib-rehberleri)
- [MASAK notice: suspicious transaction reporting guides updated, 11 September 2025](https://masak.hmb.gov.tr/duyuru/supheli-islem-bildirim-rehberleri-guncellenmistir-rehberlere-buradan-erisim-saglayabilirsiniz)
- [MASAK banking guide update, 14 May 2024](https://masak.hmb.gov.tr/duyuru/supheli-islem-bildirimi-rehberi-bankacilik-ve-masak-online-sistemi-guncellendi)
- [Law No. 5549 on Prevention of Laundering Proceeds of Crime](https://masak.hmb.gov.tr/5549-sayili-suc-gelirlerinin-aklanmasinin-onlenmesi-hakkinda-kanun-2)
- [MASAK Measures Regulation](https://masak.hmb.gov.tr/suc-gelirlerinin-aklanmasinin-ve-terorun-finansmaninin-onlenmesine-dair-tedbirler-hakkinda-yonetmelik-3/)
- [MASAK General Communiqué No. 13](https://masak.hmb.gov.tr/masak-genel-tebligi-sira-no-13/)
- [MASAK typologies](https://masak.hmb.gov.tr/tipolojiler)
- [FATF Recommendations, updated June 2026](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html)
- [FATF risk-based approach for the banking sector](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Risk-based-approach-banking-sector.html)
- [FATF Recommendation 1 proportionality update, February 2025](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/update-standards-promote-financial-conclusion-feb-2025.html)
- [FATF Recommendation 16 payment-transparency update, June 2025](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/update-Recommendation-16-payment-transparency-june-2025.html)
- [FATF beneficial-ownership guidance](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html)
- [United Nations Security Council Consolidated List](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list)

## Important boundaries

- The repository does not redistribute the UN list or any real screening record.
- `synthetic_watchlist_match` is random synthetic test data and is never represented as a real match.
- `XH` is fictitious. The remaining country codes support synthetic routing only; their scores are not official ratings.
- MASAK typologies inspired scenario coverage, but this implementation is not an official MASAK rulebook.
- Current sanctions and jurisdiction classifications must be sourced through approved, licensed and regularly refreshed production services.
