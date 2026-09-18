# Development history

The first public `main` branch is a source snapshot. Earlier protocol, exploratory,
implementation and result commits are preserved without rewriting their objects
in [`development-history.bundle`](development-history.bundle).

```bash
git bundle verify docs/development-history.bundle
git fetch docs/development-history.bundle HEAD:refs/heads/development-archive
git log --oneline development-archive
```

The archive ends at `94ff370`. It does not include the later sequence-pair
analysis or current presentation edits, which are in the public source snapshot.
Commit ancestry records local development order; local commit timestamps are
not independent proof of external preregistration. Published research claims
must be supported by the protocols, row-level artifacts and reproduction checks.
