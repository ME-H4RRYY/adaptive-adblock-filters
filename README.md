# Adaptive Ad Blocker public filter feed

This repository hosts the generated community filter data consumed by the Adaptive Ad Blocker extension. It is separate from the private extension source repository.

## Published files

- `extension/remote-rules.json`: validated domain-only blocking rules compiled from public filter lists.
- `extension/domain-model.json`: a small Naive Bayes review model and evaluation metadata. It is advisory; it does not choose blocking rules.
- `tools/`: the Python standard-library compiler and model trainer used by automation.
- `NOTICE-FILTER-SOURCES.md`: source attribution and licensing notes.

The feed contains no browsing history, page content, or user reports. Downloading it from GitHub exposes ordinary connection metadata, including the request IP, to GitHub.

## Updates

GitHub Actions runs the compiler weekly and can also run it manually. Updates are committed only when generated output changes. The extension validates downloaded data before applying it. Filter updates do not update executable extension code.

## Sources and limitations

The compiler supports a conservative domain-rule subset of EasyList and EasyPrivacy. It does not implement cosmetic rules, redirects, scriptlets, or all filter syntax. False positives and missed ads are possible. Review `NOTICE-FILTER-SOURCES.md` before redistributing the feed; the upstream lists have attribution and license requirements.
