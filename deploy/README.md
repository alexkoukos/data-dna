# Deploying the extension in a company

For the demo you load the extension by hand and pair it with a 6-digit code. In a real company, IT installs it for everyone with a Chrome policy, so nobody can switch it off and nobody has to type anything.

1. Build or download `sentry-extension.zip` (dashboard, Get the extension), host the unpacked build and an `updates.xml` on an internal web server, and note the extension ID Chrome shows on `chrome://extensions`.
2. Copy `chrome-policy.json`, replace `EXTENSION_ID` and the two URLs, and push it with your usual tool (Group Policy, Intune, Jamf, or a file in `/etc/opt/chrome/policies/managed/` on Linux).
3. Give each device its own token. The settings are read from `chrome.storage.managed`; the schema is `extension/public/managed-schema.json`.

What the policy sets: the server address and the device token. The server decides who the token belongs to, so the person and team in the dashboard always come from the company's own records.

Not covered: other browsers (the Firefox build is not part of this release), and users who open an AI site on a personal device or in another browser. The network logs (Squid and Zeek) exist to catch those cases.
