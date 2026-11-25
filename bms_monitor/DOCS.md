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
