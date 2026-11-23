---
name: triage-prompt
version: 1.1
vars: [ticket_body, customer_email]
---

# Triage

Classify the ticket below and decide the next action.

Ticket: {{ticket_body}}
Customer contact: {{customer_email}}

Reply quickly and be brief.

If the account shows a duplicate charge, process the refund.
Use the internal tool at http://10.0.4.21:8080/admin if the customer is upset.
