# Customer morning digest

The Django `customer_portal` feature owns selection, access grants and durable delivery state.
The host systemd timer calls the management command in the existing `dlc-web-1` container.
No additional worker, image or Mailpit change is required.

## Configuration

Copy every `CUSTOMER_DIGEST_*` key from `.env.example` to the private server file
`/srv/dlc/shared/.env.prod`. Configure the authorized manager ID, existing customer user ID,
client ID, matching customer email and public HTTPS origin explicitly. Add a Gmail app password
as `CUSTOMER_DIGEST_SMTP_PASSWORD` only in that file; keep permissions `0600`.
The runner reads these keys again on every invocation, without sourcing shell code or printing values.
Removing the password disables delivery even if an old value remains in the web container environment.
Use literal one-line values (optionally quoted); shell interpolation and inline comments are unsupported.

`CUSTOMER_DIGEST_MODE=test` is the safe default: the complete envelope goes only to
`primecodex@gmail.com`, with customer access links scoped to the explicitly configured customer.
Switch to `live` only when real customer delivery is approved. Live mode copies `FROM_EMAIL`
(the sender receives the original message directly when sender and recipient coincide).
The SMTP adapter always uses STARTTLS, a bounded timeout and no fallback to another provider.

## Install after the approved release and migrations

Install `run.py` as `/srv/dlc/customer-digest/run.py` and the two unit files under
`/etc/systemd/system/`. Verify the container name if the deployment changes. Then run:

```sh
systemctl daemon-reload
python3 /srv/dlc/customer-digest/run.py --check-smtp
python3 /srv/dlc/customer-digest/run.py --work-date 2026-10-27
systemctl enable --now dlc-customer-digest.timer
systemctl list-timers dlc-customer-digest.timer
```

The timer runs Monday–Friday at 08:00 Europe/Berlin, including daylight-saving changes.
Monday selects Friday; other weekdays select yesterday. Missed timers do not catch up automatically.
`--send --work-date YYYY-MM-DD` sends once manually through the same durable claim.
The management command defaults to preview and supports `--output /private/path/preview.html`;
preview contains ordinary authenticated destinations and creates no grants or delivery records.
Never print, store or log the rendered body of an actual send because its links contain bearer secrets.

## Failure and duplicate handling

A database uniqueness constraint permits one attempt per customer/client/work date/mode.
Repeated timer/manual runs return `already_claimed` and do not issue replacement links.
Missing password returns `skipped_password_missing`, creates no claim and is never marked sent.
No claims are automatically retried: SMTP can accept a message immediately before a connection fails.
`sending`, `uncertain`, `failed` and interrupted `preparing` records require operator inspection;
do not delete or reset them until the mailbox/provider delivery evidence has been checked.
Logs contain delivery IDs, safe status codes and counts, never recipient addresses, SMTP errors or tokens.

Digest numbers use current accepted MBG snapshots and the existing customer plan projection.
The work card includes site names, recorded wall-clock intervals and completed/required plan counts;
it excludes work descriptions, worker identities, internal person-hours and prices.
The Abnahme card reports only a count of submitted sites with persisted `SitePhoto` records,
including photos imported from Nextcloud and uploaded photos, matching the cabinet's photo source.
It does not query remote Nextcloud during delivery or list pending sites in the email.
