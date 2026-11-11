# Community filter sources and licensing

This repository compiles a limited, domain-only subset of these public lists:

- EasyList: <https://easylist.to/easylist/easylist.txt>
- EasyPrivacy: <https://easylist.to/easylist/easyprivacy.txt>
- License terms: <https://easylist.to/pages/licence.html>

The EasyList license page states that repository contents, unless otherwise noted, are dual licensed under GPL version 3 or any later version, or CC BY-SA 3.0 or any later version. The project selects the GPL version 3 option for the included source-derived material and distributes the generated subset and model under GPL-3.0-only. Attribution requested by EasyList: **The EasyList authors** — <https://easylist.to/>. The compiler retains the exact downloaded list bytes in `source-snapshots/` and records their hashes, sizes, URLs, and build metadata in generated artifacts. Each snapshot is committed alongside the output it generated; prior snapshots remain available in Git history.

The model uses weak labels extracted from exact-domain block and exception syntax. It only reports advisory quality metrics; it does not control blocking decisions or invent domains. The project applies the same GPL-3.0-only distribution policy to the model and publishes the source snapshots and compiler/training code needed to reproduce it.

The compiler and repository materials are licensed under GPL-3.0-only; see `LICENSE`. This license choice does not transfer ownership of upstream material. Upstream copyright and notices remain with their respective authors. The current generated artifacts predate source snapshots; their exact source bytes were not retained, and hashes cannot be reconstructed from current upstream lists.
