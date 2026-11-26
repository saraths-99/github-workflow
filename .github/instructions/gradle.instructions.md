---
applyTo: "**/*.gradle.kts,**/libs.versions.toml"
---

# Gradle conventions

- Dependency versions are declared once in `libs.versions.toml` and referenced by alias — don't
  hardcode a version string directly in a module's `build.gradle.kts`.
- Local builds use the `isLocalBuild` flag where a module defines it, to switch between an
  Artifactory-published AAR and the local project dependency — check whether the module you're
  touching has this switch before assuming a dependency is always a project reference.
- `isLocalBuild=true` in a repo's `gradle.properties` is for building locally only. It must be
  `false` in anything committed: `qatalyst-ticket-ship` resets it before committing and puts it back
  afterwards. Don't make it `true` in a committed file by hand either.
- Never edit a signing config, keystore reference, or credentials block, and never read their
  contents.
- A new module is added to `settings.gradle.kts` and to the module map in `copilot-instructions.md`
  in the same change — don't let the two drift apart.
- `qatalyst-ticket-ship` builds with `isLocalBuild=true` before committing — a Gradle change that breaks
  that configuration blocks the commit, not just a later pipeline run.
