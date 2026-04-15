---
layout: default
title: PyPI publishing
nav_order: 90
---

# PyPI publishing (maintainers)

Releases use **Trusted Publishing** (OIDC) — no long-lived PyPI password in GitHub secrets.

## One-time PyPI setup

1. **Create the project** on [PyPI](https://pypi.org/) if it does not exist yet (`easy-aso` must match `name` in `pyproject.toml`).
2. Open **Your project → Publishing** (or account **Publishing** for a new pending publisher).
3. **Add a new pending publisher** → **GitHub**:
   - **Repository:** `bbartling/easy-aso`
   - **Workflow name:** `publish-pypi.yml` (file under `.github/workflows/`)
   - **Environment name:** leave blank unless you add a GitHub Environment named `pypi` later.
4. Save. PyPI will trust OIDC tokens from that workflow only.

Official guide: [Trusted Publishers](https://docs.pypi.org/trusted-publishers/).

## Cutting a release

**Merging a PR to `master` does not publish to PyPI.** Only a **`git push` of a tag matching `v*`** runs the publish job (see `if: startsWith(github.ref, 'refs/tags/v')` in `publish-pypi.yml`). CI on branch pushes is separate (`ci.yml`).

### Order matters (read this once)

PyPI publishes **whatever commit the tag points at**. A **version-only** merge (e.g. “bump `pyproject.toml`”) does **not** magically include code that still lives in a **separate open PR**.

1. **Merge every PR that carries the release code** into `master` **first** (e.g. your `release/…` or feature branch).
2. **Then** bump `version` in `pyproject.toml` (same PR as the code, or a follow-up PR — both are fine **after** the code is on `master`).
3. **Only then** tag `master` and push the tag.

If you tag after only step (2), you can ship a **new version number with old code**. **PyPI cannot be overwritten** for that version — you must publish a **newer** `version` (e.g. `0.1.7`) with the correct tree.

### Before you push the tag — quick verify

After `git pull origin master`, confirm the tree matches what you intend (examples below; adjust for your release):

```bash
grep ^version pyproject.toml
test -f easy_aso/runtime/rpc_docked.py   # example: RPC-docked runtime present
```

Or: `git merge-base --is-ancestor origin/<your-release-branch> HEAD` should succeed **before** tagging.

---

Typical flow:

1. Open a PR from **`develop`** (or a feature / **`release/…`** branch) into **`master`** with **all code changes** for the release. Merge it.
2. Ensure **`pyproject.toml` `version`** on `master` matches the release you will tag (bump in another PR if needed).
3. On your machine, update local **`master`** and create the tag **on that merge commit**:

   ```bash
   git checkout master
   git pull origin master
   git tag vX.Y.Z   # must match version in pyproject.toml (with leading v)
   git push origin vX.Y.Z
   ```

   Tags pushed from **`develop`** before merging still publish whatever commit the tag points to — for a clean release, the tag should usually point at **`master`** after the merge.

4. Watch **Actions → Publish easy-aso to PyPI**. The workflow runs **pytest** on **Python 3.11 and 3.12**, builds with **Python 3.12**, then **Trusted Publishing** uploads **`dist/*`** for that tag.

`workflow_dispatch` runs the same **test** and **build** jobs; **Publish to PyPI** runs only when the workflow run was triggered by a **tag** (`refs/tags/v*`).

## If publish fails

- **“Permission denied” / OIDC:** Workflow filename or repository on PyPI must match exactly.
- **“File already exists”:** You cannot overwrite a given version on PyPI — bump the version and tag again.
