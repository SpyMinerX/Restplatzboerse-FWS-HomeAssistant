# 0.1.3

- Configurable list of course names and exact or substring matching.
- Rename display name to FWS Restplatzbörse Monitor; retain slug and persistent data.
- Normalize German umlauts and transliterations.

# 0.1.2

- Support modern notify entities via notify.send_message and retain legacy mobile_app notification actions.
- Modern notifications include the course URL in the message body.

# 0.1.1

- Fix initial installation failure: build from Python 3.12 slim and install Chromium with Playwright during Docker build.
- Docker build and live export still require verification on Home Assistant OS.

# 0.1.0

Initial beta: Playwright export, course filtering and persistent notification deduplication.
