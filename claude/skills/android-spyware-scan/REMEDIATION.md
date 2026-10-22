# Removal and securing steps

Steps the user carries out on the phone. Adapt menu names to the maker (OnePlus/ColorOS, Samsung One UI, Pixel). Give only the branches that apply to the flagged apps.

## Before removing anything: stalkerware safety

When the verdict is **compromised** and someone else may have installed the app, removing it can alert that person and cut off evidence. Tell the user, before any removal step:

1. Take screenshots of the app's info page and of these findings first.
2. Think about whether the person who installed it could react badly. If so, contact a support service before acting (in Spain: 016, free and leaves no trace on the phone bill; the Coalition Against Stalkerware at stopstalkerware.org lists services by country).
3. Do the account steps below from a different, trusted device.

## Removing an app

1. **Device admin first.** If it is a device admin: Settings → Security → Device admin apps (on OnePlus: Settings → Security & privacy → More security settings → Device admin apps), turn it off.
2. **Accessibility and notification access.** Turn them off for the app: Settings → Accessibility → Installed apps, and Settings → Notifications → Device & app notifications / Notification access.
3. **Uninstall.** Settings → Apps → [app] → Force stop → Uninstall.
4. **Blocked uninstall.** Restart into safe mode (hold power, then long-press "Power off"), which keeps third-party apps from running, and uninstall from there.
5. **VPN apps.** Also check Settings → Connections/Network → VPN and remove the profile.
6. **Accounts.** For an unknown account: Settings → Passwords & accounts → [account] → check what syncs → Remove account.
7. Check the app is gone: it no longer appears in Settings → Apps. With adb attached, `adb shell pm list packages <pkg>` returns nothing.

## Securing afterwards

- **Google**: myaccount.google.com → Security. Review "Your devices" and sign out of any you do not recognise, review third-party apps with account access, change the password, and turn on 2-step verification with a passkey or authenticator app rather than SMS.
- **Location**: Google Maps → profile → Location sharing; remove anyone unexpected. Also check Find My Device for other devices on the account.
- **Other accounts**: change passwords for email, banking and messaging, and log out of other sessions (WhatsApp → Linked devices, Telegram → Devices, Instagram → Account Centre → Where you're logged in).
- **Install sources**: Settings → Apps → Special app access → Install unknown apps; turn it off for every app that does not need it.
- **Play Protect**: Play Store → profile → Play Protect → Scan.
- **Compromised verdict**: after the evidence is saved and the account steps are done from a clean device, recommend a factory reset, then restore apps from the Play Store rather than from a full device backup.
