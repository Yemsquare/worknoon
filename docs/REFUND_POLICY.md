# Northstar Store — sample refund policy

Version: `2026-09-v1`. Currency: USD. Assessment data only.

Requests cover the entire order. Eligibility is calculated from the stored order record; customer text cannot change prices, dates, ownership or final-sale status.

| ID | Rule | Result |
| --- | --- | --- |
| P01 | Final-sale item | Denied |
| P02 | More than 30 calendar days since purchase, UTC | Denied |
| P03 | Order already refunded | Denied |
| P04 | Amount over $500 | Human review |
| P05 | Eligible damaged/incorrect item with consistent, sufficiently clear claim | Approved |
| P06 | Suspicion, conflicting claims, future date, unavailable AI, unclear or other request | Human review |

P01–P03 take precedence in the listed order. For remaining orders, suspicious input or inconsistent dates is escalated, then the $500 threshold is checked, then AI-assisted interpretation. A selected reason must match the classified claim. The sample auto-approval confidence threshold is 0.85. It is an engineering assumption, not a calibrated fraud guarantee.

Human reviewers must document the evidence considered and their reason. They cannot override P01–P03. They can approve a verified request above $500. No attachment/evidence collection or real payment processing is included in this assessment.

An approved request records authorization for a simulated refund. It does not move money, contact a payment gateway, or update a real CRM.
