.. role :: date(kbd)

###########
Changelog
###########

This project uses Semantic Versioning -- https://semver.org

===============
Version list
===============

.. default-role:: code


1.0.0 :date:`Oct 23`
---------------------
- Extracted from es7s/core

1.3.0 :date:`Nov 23`
--------------------
- 🌱 NEW: `common.bcs` `common.lcm`
- 💎 REFACTOR: `progressbar.ProgressBar._format_ratio_bar()`

1.4.0 :date:`Dec 23`
---------------------
- 🌱 NEW: `termstate.terminal_state` context manager
- 💎 REFACTOR: `logger` instantiating
- 🐞 FIX: dependencies
- 🐞 FIX: `progressbar` component
- 🐞 FIX: removed debug instruction
- 🐞 FIX: `RenderableColor` signature
- ❌ REMOVAL: `joincoal` `isempty` `filtere` `filterev` -> to pytermor

1.6.0 :date:`Dec 23`
---------------------
🌱 NEW: `TextStat`, `columns`, `URL_REGEX`, `UCS_CYRILLIC`, `UCS_CONTROL_CHARS`
🌱 NEW: `TerminalState.set_horiz_tabs()`
🆙 UPDATE: `plang`

1.7.0 :date:`Feb 24`
---------------------
🆙 UPDATE: `column` signature and gap computation logic

1.7.1 :date:`Feb 24`
---------------------
🐞 FIX: applying section gap for all cases
