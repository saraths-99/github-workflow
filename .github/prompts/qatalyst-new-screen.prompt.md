---
mode: agent
description: Add a new screen (Compose screen, ViewModel, nav destination, test).
---

Run the `qatalyst-new-screen` skill for the screen described in the argument: build a new screen in
Jetpack Compose (a change to an existing screen stays in its XML layout, with its Fragment extending
`BaseFragment`), register the ViewModel in `AppModule.kt`, add the nav destination with Safe Args,
then hand off to `qatalyst-test-writer` for the ViewModel test.
