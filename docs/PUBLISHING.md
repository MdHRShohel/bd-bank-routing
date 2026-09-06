# Publishing

Nothing here publishes itself. Every step below is a deliberate command someone
runs, and the registry credentials are not in this repo.

Run the gate first — it builds everything, runs both suites, and then installs
both packages into throwaway environments and uses them:

```bash
./scripts/check.sh
```

That last tier matters more than it looks. The JS package once passed all 29 of
its tests and was still broken on install: importing a `.json` file works under
vitest and under every bundler, and throws `ERR_IMPORT_ATTRIBUTE_MISSING` under
plain Node ESM. Only installing the built artifact catches that.

## 0. Before anything: the site URL

`SITE_URL` in [`scripts/seo.py`](../scripts/seo.py) is the single value that every
canonical tag, sitemap entry and Open Graph tag is generated from. It is
currently:

```
https://mdhrshohel.github.io/bd-bank-routing
```

If the site is going anywhere else — a custom domain, say — change it there and
re-run `./scripts/check.sh` before publishing. A canonical tag pointing at a host
that does not serve the page is worse than having no canonical tag at all.

## 1. GitHub

```bash
gh repo create MdHRShohel/bd-bank-routing --public \
  --description "Bangladesh bank, branch and BEFTN routing numbers — with the receipts" \
  --source . --remote origin --push
```

Then add the topics people search: `bangladesh`, `banking`, `routing-number`,
`beftn`, `fintech`, `payroll`, `open-data`, `dataset`.

## 2. The site (GitHub Pages)

`site/` is committed already built, so Pages needs no build step.

1. Repository → **Settings → Pages → Source: GitHub Actions**.
2. Push to `main`. [`.github/workflows/pages.yml`](../.github/workflows/pages.yml)
   publishes `site/`.
3. Confirm `https://mdhrshohel.github.io/bd-bank-routing/` serves, then submit
   `sitemap.xml` in Google Search Console. The 63 per-bank pages are the ones
   that will pick up long-tail traffic ("sonali bank routing number"), so they
   are the ones worth watching in Search Console.

## 3. npm

npm, yarn, pnpm and bun all install from the same registry, so this is **one**
publish, not four.

Both registries now publish from CI on a tag, with no credential anywhere:

```bash
# bump both versions together, then
git tag -a v0.1.2 -m "v0.1.2" && git push origin v0.1.2
```

`prepublishOnly` rebuilds and re-runs the tests, so a broken build cannot be
published by accident.

Verify:

```bash
npm view bd-bank-routing
cd /tmp && mkdir t && cd t && npm init -y && npm install bd-bank-routing
node --input-type=module -e 'import {lookup} from "bd-bank-routing"; console.log(lookup("225150135"))'
```

## 4. PyPI

```bash
cd packages/python
uv build
uv publish --token pypi-<token>     # or: twine upload dist/*
```

Verify:

```bash
pip install bd-bank-routing
python -c "import bdbanks; print(bdbanks.lookup('225150135'))"
```

The install name is `bd-bank-routing` and the import name is `bdbanks`, the way
`beautifulsoup4` imports as `bs4`. Both were free on both registries as of
2026-09-06.

## Gotchas that cost a whole afternoon

All three of these fail with an error that names something other than the cause.

**`setup-node` with `registry-url:` breaks OIDC.** It writes an `.npmrc` pinning
the auth token to `$NODE_AUTH_TOKEN` and exports that variable as the literal
string `XXXXX-XXXXX-XXXXX-XXXXX`. npm then attempts token auth with the
placeholder, fails `ENEEDAUTH`, and never reaches the OIDC exchange. Omit
`registry-url` entirely when publishing via trusted publishing.

**npm OIDC needs npm >= 11.5.1**, and Node 22 still ships npm 10.x. Same
`ENEEDAUTH`, no mention of the version. `npm install -g npm@latest` first.

**npm has no pending-publisher concept.** Trusted publishing is configured on an
existing package, so the very first version has to be published another way —
`npm login && npm publish` from a terminal, entering the OTP by hand. Do not
create a bypass-2FA token for this; npm warns against it, and it is only needed
once. After that first publish, set up the trusted publisher and never hold a
token again. When configuring it: **Environment must be blank** (the npm job has
no `environment:`), and **Allow `npm publish`** must be ticked or only staged
publishes are permitted and releases silently never ship.

PyPI, by contrast, supports a *pending* publisher, so it can publish a
brand-new project from CI with no manual first release and no token at all.

---

## 5. Releasing again later

The dataset is a snapshot, and the version is the date it was generated. When
captures are re-checked:

1. Update the capture files under `data/sources/`, keeping `# checked:` honest.
2. `./scripts/check.sh` — the build refuses to emit a dataset that contradicts
   itself, so this is where a bad edit stops.
3. Bump the version in `packages/js/package.json` and
   `packages/python/pyproject.toml` together. They ship one dataset; they should
   never carry different version numbers.
4. Publish both. Publishing one and not the other is how the two drift.
