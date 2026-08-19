"""Seeds a 5-word dictionary and exercises the whole pipeline.
No spaCy, no network. Run: python3 smoke_test.py"""
import json, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(__file__))
from app import deck, render
from app.dictionary import Dictionary, split_compound
from app.resolve import Ref

SCHEMA = open(os.path.join(os.path.dirname(__file__), "schema.sql")).read()


def seed(path="/tmp/dict.sqlite"):
    if os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    rows = [
        # lemma pos gender plural gen aux sep part refl p3 pret pii governs ipa
        ("Haus", "NOUN", "das", "die Häuser", "des Hauses", None, 0, None, 0,
         None, None, None, "[]", "haʊ̯s"),
        ("Karte", "NOUN", "die", "die Karten", None, None, 0, None, 0,
         None, None, None, "[]", "ˈkaʁtə"),
        ("Versicherung", "NOUN", "die", "die Versicherungen", None, None, 0,
         None, 0, None, None, None, "[]", None),
        ("Kranken", "NOUN", "die", None, None, None, 0, None, 0,
         None, None, None, "[]", None),
        ("anrufen", "VERB", None, None, None, "haben", 1, "an", 0,
         "ruft an", "rief an", "angerufen", '["Akkusativ"]', "ˈanˌʁuːfn̩"),
        ("groß", "ADJ", None, None, None, None, 0, None, 0,
         None, None, None, "[]", "ɡʁoːs"),
    ]
    for r in rows:
        db.execute(
            "INSERT INTO lemma (lemma,pos,gender,plural,genitive_sg,aux,"
            "separable,particle,reflexive,praesens_3sg,praeteritum_3sg,"
            "partizip_ii,governs,ipa,ipa_source,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'wiktionary','wiktionary')", r)
    glosses = {"Haus": ["house; building", "household, family line"],
               "Karte": ["card; map; ticket"], "Versicherung": ["insurance"],
               "Kranken": ["sick"], "anrufen": ["to call, to phone"],
               "groß": ["big, large, tall", "great, major"]}
    for lem, gs in glosses.items():
        lid = db.execute("SELECT id FROM lemma WHERE lemma=?", (lem,)).fetchone()[0]
        for i, g in enumerate(gs):
            db.execute("INSERT INTO sense (lemma_id,ord,gloss_en,source,license)"
                       " VALUES (?,?,?,'wiktionary','CC-BY-SA-3.0')", (lid, i, g))
    db.execute("UPDATE lemma SET comparative='größer', superlative='größten'"
               " WHERE lemma='groß'")
    # one Tatoeba-shaped example, linked to anrufen
    db.execute("INSERT INTO example (id,de,en,source,source_ref,license,"
               "token_count,has_proper) VALUES (1,'Ruf mich morgen an!',"
               "'Call me tomorrow!','tatoeba','12345','CC-BY-2.0',5,0)")
    lid = db.execute("SELECT id FROM lemma WHERE lemma='anrufen'").fetchone()[0]
    db.execute("INSERT INTO example_lemma VALUES (?,1)", (lid,))
    db.commit(); db.close()
    return path


def box(face, label):
    print(f"  ┌─ {label} " + "─" * (26 - len(label)) + "┐")
    if face.headline:
        print(f"  │ {face.headline[:26]:<26} │")
    if face.ipa:
        print(f"  │ [{face.ipa}]{'':<{max(0,24-len(face.ipa))}} │")
    for l in face.lines:
        print(f"  │ {l[:26]:<26} │")
    for l in face.collapsed:
        print(f"  │ ⌄ {l[:24]:<24} │")
    for e in face.examples:
        print(f"  │ {e['de'][:26]:<26} │")
        if e.get("en"):
            print(f"  │ {e['en'][:26]:<26} │")
    if face.needs_input:
        print(f"  │ ⚠ Add your translation     │")
    print("  └" + "─" * 28 + "┘")


d = Dictionary(seed())

print("=== 1. exact hit: noun ===")
e = d.lookup(Ref("Haus", "NOUN", gender="das"))
box(render.front(e, "recognition"), "FRONT"); box(render.back(e, "recognition"), "BACK")

print("\n=== 2. exact hit: separable verb ===")
e = d.lookup(Ref("anrufen", "VERB"))
box(render.front(e, "recognition"), "FRONT"); box(render.back(e, "recognition"), "BACK")

print("\n=== 3. production template (same note) ===")
box(render.front(e, "production"), "FRONT"); box(render.back(e, "production"), "BACK")

print("\n=== 4. compound fallback (no dict entry) ===")
print("  split:", split_compound("Krankenversicherungskarte", d._known_noun))
e = d.lookup(Ref("Krankenversicherungskarte", "NOUN"))
print("  status:", e.status)
box(render.back(e, "recognition"), "BACK")

print("\n=== 5. unresolved -> needs_gloss, card still created ===")
e = d.lookup(Ref("Feierabend", "NOUN", gender="der"))
print("  status:", e.status)
box(render.back(e, "recognition"), "BACK")

print("\n=== 6. deck write + FSRS ===")
if os.path.exists("/tmp/u1.sqlite"): os.remove("/tmp/u1.sqlite")
udb = sqlite3.connect("/tmp/u1.sqlite"); udb.row_factory = sqlite3.Row
udb.executescript(SCHEMA)
nid, created = deck.add_note(udb, 1, e, lesson_id="lektion04", span=(120, 130))
print(f"  note {nid} created={created}")
nid2, created2 = deck.add_note(udb, 1, e)
print(f"  re-add -> created={created2}  (dupe detection)")
cid = udb.execute("SELECT id FROM card WHERE note_id=?", (nid,)).fetchone()[0]
print("  due after Good:", deck.review(udb, cid, 3)[:19])
print("  due after Again:", deck.review(udb, cid, 1)[:19])
deck.fill_gloss(udb, nid, "end of the workday", contribute=True)
print("  reviews logged:", udb.execute("SELECT COUNT(*) FROM review_log").fetchone()[0])
print("  contributions:", udb.execute("SELECT gloss_en FROM gloss_contribution").fetchall()[0][0])
r = udb.execute("SELECT status, gloss_user FROM note WHERE id=?", (nid,)).fetchone()
print("  note now:", dict(r))
print("\nOK")
