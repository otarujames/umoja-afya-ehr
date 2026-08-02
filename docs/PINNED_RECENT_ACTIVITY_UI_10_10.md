# Umoja Afya EHR v10.10.0 — Pinned and Recent Activity UI

The activity launcher memory panel was redesigned for production use.

## Improvements

- Compact, consistent activity cards with aligned icon, title, category, pin action and navigation chevron.
- Clear empty state for pinned activities.
- Recent activities no longer float in excessive whitespace.
- Pin and unpin actions remain user-specific.
- Clear controls are visually aligned and keyboard accessible.
- Hover and keyboard-focus states use the existing tooltip and accessibility system.
- Mobile layouts retain usable touch targets and do not truncate activity names unnecessarily.

## Upgrade

Rebuild the application container without deleting the PostgreSQL volume or secrets directory.
