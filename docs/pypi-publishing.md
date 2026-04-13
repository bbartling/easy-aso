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

1. Bump `version` in `pyproject.toml` on **`master`** (open-fdd style) or your release branch, then merge.
2. Tag a **PEP 440** version with a `v` prefix (matches the workflow filter):

   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

3. Watch **Actions → Publish easy-aso to PyPI**. The job uses **Python 3.14** (same as [open-fdd `publish-openfdd-engine.yml`](https://github.com/bbartling/open-fdd/blob/master/.github/workflows/publish-openfdd-engine.yml)), runs `python -m build` at the repo root, and uploads **`dist/*`** for that tag.

`workflow_dispatch` on the same workflow can be used to **dry-run** build steps locally on CI without a tag (the **Publish to PyPI** step is skipped unless the ref is `refs/tags/v*`).

## If publish fails

- **“Permission denied” / OIDC:** Workflow filename or repository on PyPI must match exactly.
- **“File already exists”:** You cannot overwrite a given version on PyPI — bump the version and tag again.
