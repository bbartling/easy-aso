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

Typical flow:

1. Open a PR from **`develop`** (or a feature branch) into **`master`** with your changes and a **`version` bump** in `pyproject.toml` (each PyPI upload must be a new version).
2. Merge the PR so **`master`** contains the release commit.
3. On your machine, update local **`master`** and create the tag **on that merge commit**:

   ```bash
   git checkout master
   git pull origin master
   git tag v0.1.6   # must match pyproject version (with leading v)
   git push origin v0.1.6
   ```

   Tags pushed from **`develop`** before merging still publish whatever commit the tag points to — for a clean release, the tag should usually point at **`master`** after the merge.

4. Watch **Actions → Publish easy-aso to PyPI**. The workflow runs **pytest** on **Python 3.11 and 3.12**, builds with **Python 3.12**, then **Trusted Publishing** uploads **`dist/*`** for that tag.

`workflow_dispatch` runs the same **test** and **build** jobs; **Publish to PyPI** runs only when the workflow run was triggered by a **tag** (`refs/tags/v*`).

## If publish fails

- **“Permission denied” / OIDC:** Workflow filename or repository on PyPI must match exactly.
- **“File already exists”:** You cannot overwrite a given version on PyPI — bump the version and tag again.
