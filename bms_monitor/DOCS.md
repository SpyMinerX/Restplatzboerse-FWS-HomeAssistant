# FWS Restplatzbörse Monitor

Configure `notify_service` with a notification entity or mobile_app action, `interval_minutes` with the polling interval, and `courses` with a list of course names. `match_mode: exact` matches complete normalized titles; `contains` matches substrings and may include advanced courses. All schools are monitored. Only future/current-date courses with vacancies qualify. No registration is performed.

Example:
```yaml
interval_minutes: 5
notify_service: notify.mobile_app_my_phone
courses:
  - Gruppenführer
  - Zugführer
match_mode: exact
```

Beta: live export and end-to-end notification delivery still require verification.

## Optional SMTP email

Enable push and email independently. At least one channel must be enabled. Example:

```yaml
push_enabled: true
email_enabled: true
email_recipients:
  - recipient@example.com
smtp_host: smtp.example.com
smtp_port: 587
smtp_security: starttls
smtp_username: account@example.com
smtp_password: YOUR_LOCAL_PASSWORD
smtp_sender: account@example.com
```

Use STARTTLS on port 587 or implicit TLS (ssl) on port 465, as specified by your provider. Leave username and password empty for an authenticated-by-network relay supporting TLS. Credentials belong only in local Home Assistant settings; backups may contain them. Each recipient receives a separate message. Successful deliveries are tracked independently; failed deliveries are retried on subsequent checks while the course remains available. Newly enabled channels can receive currently available courses. SMTP delivery has not been tested against your server.
