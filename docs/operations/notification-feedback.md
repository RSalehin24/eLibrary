# Notification feedback

Profile settings include a notification sound preference, off by default. The
preference is local to the browser and synchronizes between tabs. If browser
storage is unavailable, the control still works for the current page and explains
that the preference could not be saved.

Legacy `app.notifications.muted` values never enable sound automatically. The old
application wrote its default unmuted value on page load, which does not establish
a reader's explicit consent. Previously muted browsers remain silent; previously
unmuted browsers can enable the new setting. A new explicit choice takes
precedence without rewriting the retained legacy value.

The application creates an audio context only after the reader explicitly enables
sound or interacts with a page where sound was already enabled. Loading a page,
restoring a saved preference and enabling the setting never play a tone. A browser
audio restriction leaves visual feedback working normally.

Successful profile saves use one shared, dismissible completion notification.
Notifications use live regions and never move keyboard focus. Repeated identical
notifications within 1.5 seconds are grouped. Existing form validation and inline
error alerts remain in place; their shared feedback component plays the optional
error tone once for each new error. Background polling and reader progress saves
do not create notifications.

Other command screens can use `useNotifications().show(message, kind)` for the
same completion/error surface, keeping a single live announcement for each event.
Do not add a second notification when the same event already has a live inline
announcement. Sound presets use the browser's Web Audio API; no external sound
files or network requests are required.

Tests cover opt-in/no-autoplay behavior, sound types, browser restrictions,
preference persistence, unavailable storage and a profile-save browser workflow.
