# Changelog

## 0.1.0
- Paused state: keep presence up with "Paused" and no progress bar for players that report `paused` (`display.show_paused`).
- Fix progress after resume: use the media position instead of the player's elapsed clock, which restarts near 0 on resume.
- Initial release: Music Assistant to Discord Rich Presence with cover art, progress bar, player filter,
  optional Jellyfin priority, interactive setup, and login service for Linux, macOS and Windows.
