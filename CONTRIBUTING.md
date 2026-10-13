# Contributing to OpenCMO

Thanks for improving OpenCMO.

OpenCMO is currently owned and maintained by [Ling (`Lling0000`)](https://github.com/Lling0000). The canonical repository is [Lling0000/OpenCMO](https://github.com/Lling0000/OpenCMO).

This project values focused contributions, clear verification, and explicit credit. This document explains how to contribute changes and how to make sure your work is correctly attributed on GitHub and in the repository.

## Ways to contribute

- Code: features, fixes, integrations, provider support, tooling, performance work
- Product polish: UX, copy, onboarding, docs, localization, screenshots
- Quality: tests, bug reports, reproducible cases, CI improvements
- Research: growth workflows, SEO or GEO improvements, competitive intelligence ideas

## Local setup

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
pip install -e ".[all]"
crawl4ai-setup
cp .env.example .env
```

Useful commands:

```bash
opencmo
opencmo-web
pytest
pytest tests/test_web.py
cd frontend && npm install && npm run build
```

## Pull request expectations

- Keep PRs focused. Split unrelated work into separate PRs.
- Explain user impact clearly.
- Add or update tests for backend changes.
- Run `npm run build` for frontend changes.
- Update docs when behavior, settings, or workflows change.
- Mention related issues, PRs, or screenshots when relevant.

## Attribution and contribution credit

OpenCMO uses three layers of contribution credit:

1. GitHub PR history: shows who proposed and discussed a change.
2. GitHub Contributors graph: shows the top commit contributors on the default branch.
3. Repository docs: `README*` and `CONTRIBUTORS.md` provide explicit human-readable credit.

GitHub's default Contributors graph is not based on the PR opener alone. According to GitHub's documentation, attribution depends on merged commits on the default branch and on the commit author email being linked to the contributor's GitHub account. If the commit email is not linked, the contributor may not appear in the graph even when the PR was merged.

To make sure your work is attributed correctly:

- Use a verified email address linked to your GitHub account.
- Or use your GitHub-provided `noreply` email.
- Do not use a shared or generic bot email as the only commit author if you want personal attribution.
- If you use an automation flow, keep the human contributor as the commit author or add a `Co-authored-by:` trailer with an email linked to GitHub.
- Make sure the work lands on the repository's default branch through a merged PR.

Useful GitHub docs:

- https://docs.github.com/articles/viewing-a-projects-contributors
- https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address
- https://docs.github.com/articles/why-are-my-commits-linked-to-the-wrong-user

## PR checklist

Before opening or merging a PR, confirm:

- [ ] My commits use an email linked to my GitHub account, or my GitHub `noreply` email
- [ ] If I used AI or automation, human attribution is preserved in the commit author or `Co-authored-by`
- [ ] Relevant tests or builds were run
- [ ] Docs were updated when behavior changed
- [ ] The PR description explains impact and verification

## Recognition policy

Maintainers may add contributors to `CONTRIBUTORS.md` and README contributor sections for notable code, product, or documentation work. This explicit credit is intended to complement GitHub's own attribution systems, not replace them.
