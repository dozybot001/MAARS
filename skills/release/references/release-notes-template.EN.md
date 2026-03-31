# MAARS Release Notes Template

Do not repeat the release title in the body. GitHub release titles are filled separately.

When drafting the final GitHub release body, place this English section first. Then add a standalone `---` separator line, followed by a collapsed Chinese block:

```md
<details>
<summary>中文</summary>

...

</details>
```

Keep the default note compact. Optimize for a reader to understand the release in about 15 seconds.

## Summary

One short paragraph that explains what this release means in practical terms for MAARS users.

## Changes

### Added

- Added item

### Changed

- Changed item

### Fixed

- Fixed item

## Validation

- `pytest tests/ -q`
- `cd frontend && npm run build`

## Notes (Optional)

- Include this section only when there is a real migration note, known limit, or operator-facing warning worth stating.
- If there is nothing meaningful to say here, omit the entire section.
