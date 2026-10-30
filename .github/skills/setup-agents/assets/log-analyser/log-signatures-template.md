<!--
generated-by: copilot-workflow
setup-agents seeds the "Tag -> module map" section below from a real scan of this repo's
Log.d/Log.w/Log.e call sites. "Known cause chains" starts with one worked example from the
workflow's own design doc and otherwise stays empty until the developer adds a confirmed chain
after a fix lands (see log-analyser.agent.md's "Learn" note) -- never pre-filled with a guess.
-->
# Log signatures

Known cause chains, known noise tags, and the tag-to-module map `log-analyser` uses in its Link and
Map steps.

## Known cause chains

<!-- One entry per confirmed bug. Format: cause, the effects it produces, the fix that resolved it,
     and the noise it's commonly confused with. Added by the developer once a fix is confirmed --
     log-analyser only reads this section, it never writes to it. -->

### AppSync real-time hosts unresolvable (`UnknownHostException`)

- **Cause:** AppSync's real-time hosts can't be resolved (seen for `us-east-1` and `us-west-2`).
- **Effects:** every active subscription (home, user, OTAU, device) fails with `UnknownHostException`,
  followed by "WebSocket communication failed", then scheduled reconnect attempts.
- **Fix:** retry the real-time host resolution with a short backoff before failing the subscription,
  instead of surfacing the first DNS failure immediately.
- **Noise commonly confused with it:** BLE discovery and key-manager chatter running at the same
  time is unrelated — check whether BLE scanning itself is succeeding before treating it as part of
  this chain.
- **Disproving check:** confirm whether the device was offline entirely (no connectivity) or online
  with DNS failing specifically — the two have different fixes.

## Known noise tags

<!-- Tags that are usually not relevant to a bug's root cause, beyond logcat_trim.py's built-in
     defaults. Add a tag here, with a one-line reason, once you've confirmed it's noise for this
     app specifically. -->

| Tag | Why it's noise |
|---|---|
|  |  |

## Tag → module map

<!-- Seeded by setup-agents from a scan of Log.d/Log.w/Log.e call sites across the open repos.
     Re-run setup-agents (via setup-workflow) to refresh this after adding new log call sites. -->

| Tag | Module |
|---|---|
|  |  |
