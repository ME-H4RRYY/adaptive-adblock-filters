# Community filter sources

The automated update workflow compiles a deliberately limited, domain-only subset of EasyList and EasyPrivacy. It excludes cosmetic filters, exceptions, redirects, scriptlets, and unsupported syntax. The compiler only emits third-party domain blocks to reduce the chance of breaking first-party site functionality.

- EasyList: <https://easylist.to/easylist/easylist.txt>
- EasyPrivacy: <https://easylist.to/easylist/easyprivacy.txt>

These lists are maintained by their respective communities. EasyList's current license page says repository contents, including EasyList and EasyPrivacy unless otherwise noted, are dual licensed under GPL-3.0-or-later or CC BY-SA 3.0-or-later. It requests attribution to “The EasyList authors (https://easylist.to/)” where required. This compiler uses only a subset, but the generated rules and model may still be derivative material. The generated feed includes the attribution. Select and document a compatible project license before public distribution; this note is not legal advice.

The ML training labels are extracted from exact-domain block rules and exceptions. They are weak labels from filter syntax, not independently verified ground truth. The model only reports quality metrics and low-confidence candidates; it never decides which rules the extension blocks or invents domains. Derived model artifacts may carry upstream attribution or license requirements; confirm those terms before publication.
