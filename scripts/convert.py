#!/usr/bin/env python3
"""Convert the Modern AGE Cyberpunk Slice PDF into Foundry pack sources for the AGE System.

Usage: scripts/convert.py PATH/TO/Modern_AGE_-_Cyberpunk_Slice.pdf [--out packs/_source] [--only focuses,talents,...]

The PDF is read with `pdftotext` and `pdftohtml` (poppler-utils) and is never stored in the repository.
Output is one JSON per document in packs/_source/<pack>/, plus `_folder-*.json` for folders.
Ids are deterministic (hash of pack + name), so reruns produce stable diffs.

Page numbers below are PDF pages (printed page number + 1).
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blocks import blocks, entries, paras, text  # noqa: E402
from common import (ABILITIES, Pack, esc, journal_doc, li, make_id, modifier, num, p, parse_ranges, pdftotext,  # noqa: E402
                    table_doc, table_html)

ABL_PATTERN = "|".join(ABILITIES)
CLASSES = {"Outsider": "Outsider", "Lower": "Lower Class", "Middle": "Middle Class", "Upper": "Upper Class"}


def squash(s):
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------- focuses (p13)

FOCUS = re.compile(r"^(" + ABL_PATTERN + r") \(([^)]+)\): (.+)$")


def build_focuses(pdf):
    pack = Pack("focuses")
    for t in paras(blocks(pdf, 13, 14)):
        m = FOCUS.match(squash(t))
        if m:
            abl, name, desc = m.groups()
            pack.item(squash(name), "focus", {
                "longDesc": p(desc), "shortDesc": "", "useAbl": ABILITIES[abl], "initialValue": 2, "improved": False,
                "isOrg": False,
            }, "gift-of-knowledge.svg", folder=f"{abl} Focuses", uid=f"{abl}:{name}")
    return pack


# --------------------------------------------------------------------------- talents and specializations (p14-19)

DEGREE = re.compile(r"^(Novice|Expert|Master):\s*(.*)$")
REQ = re.compile(r"^Requirements?:\s*(.*)$")


def parse_talent(bl):
    """(requirement, description, {degree: [texts]}, other blocks) from the blocks under a talent heading."""
    req, desc, deg, key, rest = "", [], {"Novice": [], "Expert": [], "Master": []}, None, []
    for b in bl:
        if b[0] not in ("p", "li"):
            rest.append(b)
            continue
        t = text(b[1])
        m = DEGREE.match(t)
        if m:
            key = m.group(1)
            deg[key].append(m.group(2))
        elif REQ.match(t) and not req:
            req = REQ.match(t).group(1)
        elif key is not None and not rest:
            deg[key].append(t)      # a degree can run over several paragraphs
        else:
            desc.append(t)
    return req, desc, deg, rest


def talent_system(kind, req, desc, deg, extra=""):
    system = {"longDesc": "".join(p(x) for x in desc) + extra, "shortDesc": "", "requirement": req, "type": kind, "degree": 0, "activate": True}
    for i, d in enumerate(("Novice", "Expert", "Master")):
        system[f"degree{i}"] = {"desc": "".join(p(x) for x in deg[d]), "isActive": True}
    return system


CYBORG_BENEFITS = ("Armored", "Disposable Body", "Optimized (Synthetic Body)", "Precision", "Ruggedized", "Secure", "Surge", "Tactical")


def fix_split_talents(ents):
    """Two talents are cut in pieces by sidebars on pages 14-15 and 18 (a two-column layout with boxes in between).

    Reassemble them explicitly; the asserts make the converter fail loudly if the text ever changes."""
    by = {t: (t, par, list(b)) for t, par, b in ents}
    out = []
    # Cybercombat Style: the end of its Expert degree and its Master degree follow the 'Sacrifice Augmentation' sidebar entry
    sac = by["Sacrifice Augmentation Special"]
    cont = [b for b in sac[2] if b[0] == "p"][1:]
    assert len(cont) == 2 and text(cont[1][1]).startswith("Master:"), "unexpected cybercombat layout"
    cyber = by["Cybercombat Style"]
    cyber[2].extend(cont)
    # Kinetic Talent: Expert and Master degrees sit in the middle of the Cyborg benefits (Precision and Tactical)
    prec, tact = by["Precision"], by["Tactical"]
    exp_i = next(i for i, b in enumerate(prec[2]) if b[0] == "p" and text(b[1]).startswith("Expert:"))
    mas_i = next(i for i, b in enumerate(prec[2]) if b[0] == "p" and text(b[1]).startswith("Master:"))
    master = text(prec[2][mas_i][1])
    cut = master.index("augmentation-improved test")
    tail = master[cut:]
    stray = [b for b in tact[2] if b[0] == "p"][1]
    assert text(stray[1]).startswith("use a different attack"), "unexpected tactical layout"
    kin = by["Kinetic Talent"]
    kin[2].append(prec[2][exp_i])
    kin[2].append(("p", master[:cut].rstrip() + " " + text(stray[1])))
    tact[2].remove(stray)
    prec[2][:] = [b for i, b in enumerate(prec[2]) if i not in (exp_i, mas_i)]
    prec[2][0] = ("p", text(prec[2][0][1]) + " " + tail)
    for t, par, b in ents:
        out.append((t, par, by[t][2] if t in by else b))
    return out


def build_talents(pdf):
    pack = Pack("talents")
    bl = blocks(pdf, 14, 20)
    ents = fix_split_talents(entries(bl, 3))
    # cyborg benefits are level-3 headings that belong to the Cyborg specialization
    benefits = {t: [x for x in b[: next((i for i, y in enumerate(b) if y[0] == "h" and y[1] <= 2), len(b))]] for t, _, b in ents if t in CYBORG_BENEFITS}
    for title, parent, body in ents:
        if not title or title in CYBORG_BENEFITS or not any(b[0] == "p" and REQ.match(text(b[1])) for b in body):
            continue
        spec = title.endswith(" Talent")
        name = title[: -len(" Talent")] if spec else title
        cut = next((i for i, b in enumerate(body) if b[0] == "h" and b[1] <= 2), len(body))
        body = body[:cut]       # the next specialization's heading and text follow in the same page flow
        req, desc, deg, rest = parse_talent(body)
        extra = ""
        if title == "Cybercombat Style":
            req, desc, deg = cybercombat(body)
            extra = qualities_html(body)
        if spec:
            flavor = spec_flavor(bl, name)
            desc = flavor + desc
            if name == "Cyborg":
                extra = "<h3>Cyborg Benefits</h3>" + "".join(f"<h4>{esc(t)}</h4>" + "".join(p(x) for x in paras(b)) for t, b in benefits.items())
        pack.item(name, "talent", talent_system("spec" if spec else "talent", req, desc, deg, extra), "skills.svg",
                  folder="Specializations" if spec else "Talents")
    return pack


def spec_flavor(bl, name):
    """Paragraphs under the heading (H2 or H3) that introduces a specialization."""
    out, on = [], False
    for b in bl:
        if b[0] == "h":
            if on:
                if b[2] == f"{name} Talent":
                    break
                if b[1] <= 3 and b[2] in CYBORG_BENEFITS:
                    continue
            on = b[2] == name
        elif on and b[0] in ("p", "li"):
            out.append(text(b[1]))
    return out


def cybercombat(body):
    """Cybercombat Style: its Expert degree is cut by the sidebar of qualities, which has to be separated from the talent."""
    ps = [text(b[1]) for b in body if b[0] == "p"]
    req = REQ.match(ps[0]).group(1)
    desc = [ps[1]]
    deg = {"Novice": [], "Expert": [], "Master": []}
    expert_tail = next(t for t in ps if t.startswith("fully defend against"))
    for t in ps:
        m = DEGREE.match(t)
        if m and m.group(1) == "Novice":
            deg["Novice"].append(m.group(2))
        elif m and m.group(1) == "Expert":
            deg["Expert"].append(m.group(2).rstrip("-") + expert_tail)   # '...success-' + 'fully defend...'
        elif m and m.group(1) == "Master":
            deg["Master"].append(m.group(2))
    return req, desc, deg


def qualities_html(body):
    """The sidebar of cybercombat qualities: h4 name, an italic prerequisite line and a description."""
    html_, started = "", False
    for b in body:
        if b[0] == "p" and text(b[1]).startswith("You may take the following cybercombat qualities"):
            started = True
            html_ += p(text(b[1]))
        elif b[0] == "h" and b[1] == 4:
            started = True
            html_ += f"<h4>{esc(b[2])}</h4>"
        elif started and b[0] == "p":
            t = text(b[1])
            if DEGREE.match(t) or t.startswith("fully defend against"):
                continue
            if len(t) < 45 and not t.endswith(".") and html_.endswith("</em></p>"):
                html_ = html_[: -len("</em></p>")] + " " + esc(t) + "</em></p>"     # second line of a prerequisite
            elif t[:1].islower() and html_.endswith("</p>"):
                html_ = html_[:-4] + " " + esc(t) + "</p>"       # a description cut by the column break
            else:
                html_ += f"<p>{b[1]}</p>" if b[1].startswith("<em>") else p(t)
    return "<h3>Cybercombat Qualities</h3>" + html_ if html_ else ""


# --------------------------------------------------------------------------- character creation (p8-13)

BG_HEAD = re.compile(r"^(?P<name>[A-Z][A-Za-z ]+?) (?P<cls>Outsider|Lower|Middle|Upper)$")
BENEFIT = re.compile(r"(\d{1,2}(?:[–-]\d{1,2})?)(\+\d [A-Za-z]+|Focus: [^()]*\([^)]*\))")
BG_ROW = re.compile(r"(\d)-(\d)\s*([A-Z][A-Za-z]+)\*?")   # class tables use a plain hyphen, benefit tables an en dash


def labelled(t, labels):
    """Split 'Ability: x Focus: y Talent: z' into a dict."""
    parts = re.split(r"\b(" + "|".join(labels) + r"):\s*", t)
    return {parts[i]: squash(parts[i + 1]) for i in range(1, len(parts) - 1, 2)}


def parse_backgrounds(pdf):
    bl = blocks(pdf, 8, 12)
    out, cur, table = [], None, None
    for b in bl:
        if b[0] == "h":
            m = BG_HEAD.match(b[2])
            if m and b[1] == 3:
                cur = {"name": m.group("name"), "cls": CLASSES[m.group("cls")], "desc": [], "fields": {}, "benefits": []}
                out.append(cur)
                table = None
            elif b[1] == 3 and b[2].startswith("Cyberpunk") and "Backgrounds" in b[2]:
                table = b[2].split()[1] if b[2].split()[1] != "Lower" else "Lower"
                table = {"Outsider": "Outsider", "Lower": "Lower Class", "Middle": "Middle Class", "Upper": "Upper Class"}.get(table)
            else:
                cur, table = None, None     # sidebar headings (special qualities) end the background text
            continue
        if b[0] != "p" or cur is None and table is None:
            continue
        t = text(b[1])
        if t.startswith("* New backgrounds in this chapter"):
            t = t[len("* New backgrounds in this chapter"):].strip()   # a paragraph of the Hazwork text continues after the footnote
            if not t or cur is None:
                continue
            cur["desc"][-1] = cur["desc"][-1] + " " + t
            continue
        if t.startswith("If it fits the campaign and the GM allows it"):
            cur = None      # start of the Special Qualities sidebar, which has no heading of its own
            continue
        if t.startswith("1d6 roll") or BG_ROW.match(t):
            continue
        if cur is None:
            continue
        if t.startswith("Ability:"):
            cur["fields"] = labelled(t, ("Ability", "Focus", "Talent"))
        elif t.startswith("2d6 roll"):
            cur["mode"] = "benefits"
            cur["benefits_text"] = t[len("2d6 roll"):].replace("benefit", "", 1)
        elif cur.get("mode") == "benefits" and re.match(r"^\d{1,2}(?:[–-]\d{1,2})?(\+\d|Focus:)", t):
            cur["benefits_text"] += " " + t
        else:
            cur["mode"] = None
            cur["desc"].append(t)
    for bg in out:
        bg["benefits"] = [(r.replace("-", "–"), squash(v)) for r, v in BENEFIT.findall(bg.pop("benefits_text", ""))]
    return out


def class_tables(pdf):
    """{class: [(lo, hi, background)]} from the four 'Cyberpunk ... Backgrounds' tables."""
    bl = blocks(pdf, 8, 8)
    out, cls = {}, None
    for b in bl:
        if b[0] == "h" and b[1] == 3 and b[2].startswith("Cyberpunk") and "Backgrounds" in b[2]:
            word = b[2].split()[1]
            cls = {"Outsider": "Outsider", "Lower": "Lower Class", "Middle": "Middle Class", "Upper": "Upper Class"}[word]
            out[cls] = []
        elif cls and b[0] == "p":
            t = text(b[1])
            if t.startswith("*"):
                cls = None
                continue
            for lo, hi, name in BG_ROW.findall(t):
                out[cls].append((int(lo), int(hi), name))
    return out


PROF_HEAD = re.compile(r"^(?P<name>[A-Z][A-Za-z ]+?) (?P<tags>(?:Physical|Mental|Social|Skilled|Upper|Middle|Lower|Outsider|/|,| )+)$")


def parse_professions(pdf):
    bl = blocks(pdf, 11, 13)
    out, cur = [], None
    for b in bl:
        if b[0] == "h":
            m = PROF_HEAD.match(b[2]) if b[1] == 3 else None
            if m and not b[2].startswith(("Cyberpunk", "Upper Class")) and any(x in m.group("tags") for x in ("Physical", "Mental", "Social", "Skilled")):
                tags = [x for x in re.split(r"[,/ ]+", m.group("tags")) if x]
                cur = {"name": m.group("name"), "kind": "/".join(x for x in tags if x in ("Physical", "Mental", "Social", "Skilled")),
                       "cls": next((CLASSES[x] for x in tags if x in CLASSES), ""), "desc": [], "stats": ""}
                out.append(cur)
            else:
                cur = None
            continue
        if cur is None or b[0] != "p":
            continue
        t = text(b[1])
        if t.startswith("Focus:"):
            cur["stats"] = t
        else:
            cur["desc"].append(t)
    for pr in out:
        m = re.match(r"Focus:\s*(.*?)\s*Talent:\s*(.*?)\s*Health:\s*(.*?)\s*Resources:\s*(\d+)", pr["stats"])
        pr["focus"], pr["talent"], pr["health"], pr["resources"] = m.groups() if m else ("", "", "", "0")
    return out


def parse_drives(pdf):
    bl = blocks(pdf, 12, 14)
    out, cur = [], None
    for b in bl:
        if b[0] == "h":
            cur = {"name": b[2], "desc": [], "stats": ""} if b[1] == 3 and b[2] in DRIVE_NAMES else None
            if cur:
                out.append(cur)
            continue
        if cur is None or b[0] != "p":
            continue
        t = text(b[1])
        if t.startswith("Talent:"):
            cur["stats"] = t
        else:
            cur["desc"].append(t)
    for d in out:
        f = labelled(d["stats"], ("Talent", "Improvement"))
        d["talent"], d["improvement"] = f.get("Talent", ""), f.get("Improvement", "")
    return out


DRIVE_NAMES = ["Addict", "Avenger", "Corporate", "Conspiracist", "Elite", "Revolutionary"]


def build_creation(pdf):
    pack = Pack("character-creation", "JournalEntry")
    bgs = sorted(parse_backgrounds(pdf), key=lambda x: x["name"])
    journal_doc(pack, "Backgrounds", [
        (b["name"], f"<p><em>{b['cls']}</em></p>" + "".join(p(x) for x in b["desc"]) + "<ul>" + li("Ability", b["fields"].get("Ability", ""))
         + li("Focus", b["fields"].get("Focus", "")) + li("Talent", b["fields"].get("Talent", "")) + "</ul>"
         + f"<h2>{b['name']} Benefits</h2>" + table_html(["2d6 Roll", "Benefit"], b["benefits"])) for b in bgs])
    profs = sorted(parse_professions(pdf), key=lambda x: x["name"])
    journal_doc(pack, "Professions", [
        (x["name"], f"<p><em>{x['kind'].replace('/', ', ')}, {x['cls']}</em></p>" + "".join(p(t) for t in x["desc"]) + "<ul>"
         + li("Focus", x["focus"]) + li("Talent", x["talent"]) + li("Health", x["health"]) + li("Resources", x["resources"]) + "</ul>")
        for x in profs])
    journal_doc(pack, "Drives", [
        (x["name"], "".join(p(t) for t in x["desc"]) + "<ul>" + li("Talent", x["talent"]) + li("Improvement", x["improvement"]) + "</ul>")
        for x in sorted(parse_drives(pdf), key=lambda x: x["name"])])
    return pack


def build_creation_tables(pdf):
    pack = Pack("creation-tables", "RollTable")
    for cls, rows in class_tables(pdf).items():
        table_doc(pack, f"Cyberpunk Backgrounds: {cls}", "1d6", "Step 3: Background (Cyberpunk Slice table)", sorted(rows_to_ranges(rows)), "Backgrounds")
    for cls, rows in profession_tables(pdf).items():
        table_doc(pack, f"Cyberpunk Professions: {cls}", "1d6", "Step 4: Profession (Cyberpunk Slice table)", [(n, n, name) for n, name in sorted(rows)], "Professions")
    table_doc(pack, "Cyberpunk Drive", "1d6", "Step 5: Drive (Cyberpunk Slice table)", [(n, n, name) for n, name in sorted(drive_table(pdf))], "Drives")
    for b in parse_backgrounds(pdf):
        table_doc(pack, f"Benefits: {b['name']}", "2d6", f"Step 3: {b['name']} benefit", parse_ranges(b["benefits"]), "Benefits")
    return pack


def profession_tables(pdf):
    """{class: [(1d6 roll, profession)]} from the profession tables (two side by side, then Upper Class)."""
    out = {"Lower Class": [], "Middle Class": [], "Upper Class": []}
    for b in blocks(pdf, 11, 12):
        if b[0] == "table":
            for row in b[1][1:]:
                cells = [text(x) for x in row]
                if len(cells) >= 4 and cells[0].isdigit():
                    out["Lower Class"].append((int(cells[0]), cells[1].rstrip("*")))
                    out["Middle Class"].append((int(cells[2]), cells[3].rstrip("*")))
        elif b[0] == "p":
            m = re.match(r"^([1-6])([A-Z][A-Za-z]+)\*?$", text(b[1]))
            if m and len(out["Upper Class"]) < 6 and not any(m.group(2) == n for _, n in out["Upper Class"]):
                out["Upper Class"].append((int(m.group(1)), m.group(2)))
    return out


def drive_table(pdf):
    rows = []
    for b in blocks(pdf, 12, 13):
        if b[0] == "p":
            m = re.match(r"^([1-6])(Addict|Avenger|Corporate|Conspiracist|Elite|Revolutionary)$", text(b[1]))
            if m:
                rows.append((int(m.group(1)), m.group(2)))
    return rows


def rows_to_ranges(rows):
    return [(lo, hi, name) for lo, hi, name in rows]


# --------------------------------------------------------------------------- main

BUILDERS = {"focuses": build_focuses, "talents": build_talents, "character-creation": build_creation,
            "creation-tables": build_creation_tables}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "packs" / "_source"))
    ap.add_argument("--only", default=",".join(BUILDERS))
    a = ap.parse_args()
    pdf = Path(a.pdf)
    if not pdf.is_file():
        sys.exit(f"PDF not found: {pdf}")
    for name in a.only.split(","):
        BUILDERS[name](pdf).write(a.out)


if __name__ == "__main__":
    main()
