# Public publication checklist

Before staging a CTF skills repository:

- Exclude flags and recognizable flag fragments.
- Exclude usernames, passwords, session cookies, API keys, platform tokens, and pairing URLs.
- Exclude participant email addresses and other personal data.
- Exclude live challenge IP addresses, hostnames, and private network details unless already public and necessary.
- Exclude raw challenge artifacts, dumps, screenshots, generated workspaces, and proprietary write-ups unless redistribution is permitted.
- Replace concrete endpoints and secrets in examples with obvious placeholders.
- Keep exploit guidance scoped to authorized CTF tasks.
- Inspect `git diff --cached` and the complete staged file list.
- Run a secret scan over staged text and inspect binary files manually.
- Validate every changed `SKILL.md` and each referenced relative path.
- Confirm the destination remote and branch immediately before pushing.

The public commit message should describe reusable skill and workflow changes, not solved flags.
