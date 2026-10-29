# Modern AGE Cyberpunk Slice Compendium for AGE System

A Foundry VTT v14 **module** for the [AGE System (unofficial)](https://github.com/vkdolea/age-system) (`age-system` 5.0.0+) with the
content of the **Modern AGE Cyberpunk Slice** converted to AGE System item, actor, journal and roll table documents.
It is a companion to the [Modern AGE compendium](https://github.com/Cappucceno/modern-age-compendium) and uses the same layout and tooling.

**Status: work in progress.**

| Compendium | Content |
|---|---|
| Cyberpunk Focuses | 9 `focus` items |
| Cyberpunk Talents and Specializations | 7 talents and the Cyborg, Kinetic, Virtualist and Vor specializations (`talent`, Novice/Expert/Master) |
| Cyberpunk Weapons / Armor | 5 weapons with their own damage (unarmed upgrades, baton, mono-whip, shuriken); 6 armors with Impact/Ballistic ratings and penalties |
| Cyberpunk Equipment | 38 items: special ammunition, firearm accessories, grenades and blade upgrades, medical equipment, drugs, sample IT assets, op gear (with Resources TN) |
| Augmentations | 44 augmentations from the catalog, with Capacity slots in the description |
| Drones and Vehicles | 16 `vehicle` actors: drones (Health, armor, velocity) and vehicles/exoskeletons (handling, capacity, velocity, ram, hull) |
| Cyberpunk Character Creation | journals: Chapter 1 text, 8 new backgrounds (with benefit tables), 6 professions, 6 drives |
| Cyberpunk Creation Tables | 16 roll tables: backgrounds per class, profession and drive tables, benefit tables |
| Cyberpunk Rules Tables | 8 roll tables: Hit Locations (1d6) and the Complications lists (general and 1- to 6-point) |
| Cyberpunk Rules Reference | journals: Chapter 2 (equipment text), Chapter 3 (augmentation rules) and clean Rules Tables (automation classes, IT firewall, hit locations) |
| Game Mastering and Cyberspace | journal: Chapter 4 (the genre, cyberspace, hacking) |

Some text of the book is cut in pieces by sidebars in the PDF layout. The Cybercombat Style, Kinetic Talent and Precision entries were reassembled
by hand in the converter (`fix_split_talents`), which fails loudly if the layout changes.

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
