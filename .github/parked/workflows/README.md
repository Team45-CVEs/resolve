# Workflows (parked)

Not in use. GitHub only runs workflows directly under `.github/workflows/`, so
nothing in this folder runs: no push, PR, tag, or scheduled triggers fire.

| File | What it did |
| --- | --- |
| `ci.yml` | Build and test on push to `main` and on pull requests |
| `analyze-image.yml` | Weekly (Mon 12:00 UTC) build, publish, and test of analyze-image remediations |
| `cleanup-images.yml` | Weekly (Sun 00:00 UTC) cleanup of old GHCR images |
| `publish.yml` | Publish the RESOLVE image on push to `main` |
| `docs.yml` | Deploy the `dev` docs on push to `main` |
| `release.yml` | Cut a release on `v*` tags |

To re-enable one, move it back into `.github/workflows/`:

```sh
mkdir -p .github/workflows
git mv .github/parked/workflows/ci.yml .github/workflows/
```
