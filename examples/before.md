---
name: triage-prompt
version: 1
vars: [ticket_body, customer_email]
---

# Triage

Handle the ticket below and decide what to do with it.

Ticket: {{ticket_body}}
Customer contact: {{customer_email}}

REPLY QUICKLY AND BE BRIEF BUT ALSO EXPLAIN YOUR FULL REASONING IN DETAIL.

If there are some issues, check the account and process the refund as needed.
Use the internal tool at http://10.0.4.21:8080/admin if the customer is upset.
