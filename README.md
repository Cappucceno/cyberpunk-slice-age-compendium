# Modern AGE Cyberpunk Slice Compendium for AGE System

A Foundry VTT v14 **module** for the [AGE System (unofficial)](https://github.com/vkdolea/age-system) (`age-system` 5.0.0+) with the
content of the **Modern AGE Cyberpunk Slice** converted to AGE System item, actor, journal and roll table documents.
It is a companion to the [Modern AGE compendium](https://github.com/Cappucceno/modern-age-compendium) and uses the same layout and tooling.

**Status: work in progress.**

| Compendium | Content |
|---|---|
| Cyberpunk Focuses | `focus` items |
| Cyberpunk Talents and Specializations | `talent` items (Novice/Expert/Master), including the Cyborg, Kinetic, Virtualist and Vor specializations |
| Cyberpunk Weapons / Armor | 4 weapons with damage of their own (unarmed upgrades, baton, whip, shuriken); armor with Impact/Ballistic ratings and penalties |
| Cyberpunk Equipment | ammunition, firearm accessories, grenades, medical equipment, drugs, sample IT assets and op gear (Resources TN, description) |
| Drones and Vehicles | `vehicle` actors: drones (Health, armor, velocity) and vehicles/exoskeletons (handling, capacity, velocity, ram, hull) |
| Cyberpunk Character Creation | journals: new backgrounds, professions and drives |
| Cyberpunk Creation Tables | roll tables for backgrounds, benefits, professions and drives |

## Building
Requires `poppler-utils` (`pdftotext`, `pdftohtml`), Python 3 and Node. The package `wamerican` (`/usr/share/dict/words`) is optional and improves the
repair of words hyphenated at line ends.
```bash
npm install
python3 scripts/convert.py "/path/to/Modern AGE - Cyberpunk Slice.pdf"   # PDF -> packs/_source/*.json (the PDF is not stored in the repo)
npm run build                                                            # packs/_source -> packs/<pack> (LevelDB)
```
`--only focuses,talents,...` converts a subset. The converter reads the PDF pages directly, so it is tied to the 2022 edition of the book.

## Notes
- Not tested inside Foundry yet.
- See [NOTICE.md](NOTICE.md) for copyright and credits.
