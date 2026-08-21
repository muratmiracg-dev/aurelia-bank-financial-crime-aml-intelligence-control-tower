# Portfolio project description

I designed and implemented an end-to-end AML decision-support platform for a fictional bank, combining explainable KYC risk scoring, six transaction-monitoring scenarios, Isolation Forest anomaly detection, NetworkX graph analytics, alert prioritisation and human-led case governance.

The project processes 1,800 synthetic customers, 2,250 accounts and 48,412 transactions. Validation labels are isolated from detection, and deliberately ambiguous lookalike behaviour creates realistic false-positive pressure. The verified snapshot produces 134 alerts across 126 customers, 67.91% synthetic precision and 98.91% synthetic recall. A case-operations layer manages priority, SLA, analyst queues and dispositions while prohibiting automated ŞİB/STR submission or customer restriction.

Deliverables include a tested Python package, read-only FastAPI service, SQLite database, PostgreSQL analytics, Power BI semantic assets, an 11-tab Excel investigation workbench, editable executive PowerPoint deck and sourced PDF report. The repository includes 38 automated tests, 96.53% coverage, CI, CodeQL, deterministic data generation and SHA-256 verification.

The strongest management insight is operational rather than algorithmic: 892 KYC reviews are overdue, above the 35% internal ceiling. The recommended response prioritises high-risk and alerted customers, assigns weekly remediation capacity and preserves human accountability.
