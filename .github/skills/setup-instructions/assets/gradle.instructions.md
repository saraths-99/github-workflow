---
applyTo: "**/*.gradle.kts,**/libs.versions.toml"
generated-by: copilot-workflow
---

# Gradle conventions

- Dependency versions are declared once in `libs.versions.toml` and referenced by alias — don't
  hardcode a version string directly in a module's `build.gradle.kts`.
- Local builds use the `isLocalBuild` flag where a module defines it, to switch between an
  Artifactory-published AAR and the local project dependency — check whether the module you're
  touching has this switch before assuming a dependency is always a project reference.
- Never edit a signing config, keystore reference, or credentials block — these paths are in
  `sensitive-paths.txt` and the `protect-secrets` hook denies both reads and edits of them.
- A new module is added to `settings.gradle.kts` and to the module map in `copilot-instructions.md`
  in the same change — don't let the two drift apart.
- `ticket-ship` builds with `isLocalBuild=true` before opening a PR — a Gradle change that breaks
  that configuration blocks shipping, not just the pipeline run.
