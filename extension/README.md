# Capture to Alduor

Chrome Manifest V3 extension for human-assisted capture of visible public business information into the local Alduor backend.

## Manual Setup

1. Start the backend from `backend/`.
2. Set `ALDUOR_EXTENSION_ENABLED=true` and `ALDUOR_EXTENSION_API_TOKEN=replace-with-local-random-token` in `backend/.env`.
3. Open `chrome://extensions`.
4. Enable Developer mode.
5. Load unpacked and select this `extension/` folder.
6. Open the extension settings page.
7. Set the backend URL and local extension token.
8. Click Test Connection.

Expected result: `Connected to Alduor`.

## Operating Boundary

This tool is a human-assisted research utility. It does not authorize bulk scraping or bypass any platform restriction. The operator is responsible for using it only on publicly accessible business information and in accordance with applicable platform terms and laws.

Capture starts only after the operator clicks `Capture Current Page`. The extension does not automate social-platform search, scrolling, navigation, login, messaging, pagination, downloads, anti-detection behavior, or background collection.

The extension reads visible public business information only. It does not collect passwords, cookies, private messages, browsing history, friend lists, follower lists, hidden account information, session data, or browser history.

## Manual Acceptance Checks

Facebook: open a public business page or post, click Capture Current Page, review fields, select a target, save, and confirm the Social Capture Inbox shows the capture.

Instagram: open a public professional profile or post and confirm followers/following identities are not collected and contact buttons are not clicked.

X: open a public company profile or post and confirm visible profile/post text is captured without follower harvesting.

LinkedIn: open a public company page and confirm it is accepted; open a personal profile and confirm it is rejected.

Meta Ad Library: open a visible Ad Library result and confirm visible advertiser, text, CTA, destination, and status are captured without pagination.

Layout-change check: remove expected fixture elements and confirm generic extraction still returns useful visible data with a warning instead of crashing.

