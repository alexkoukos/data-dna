"""Build the TEST set for the D7 borderline judge: data/finetune/test.jsonl (+ test_stats.md).

  python3 scripts/gen_judge_test.py --akryon /path/to/akryon_mockdata/data      (or env AKRYON_DIR)

Never trained on. The training company (data/train_org, Taygetos Oils) shares no document, person, client or
6-word run with it; the script checks that against data/finetune/{train,val}.jsonl and stops if it finds one.
Run gen_finetune.py first. Without --akryon only the eval-company parts are built (stats say so).

Two test companies:
  Akryon Systems        the teammates' mock data (documents, labelled prompts, employees, clients)
  Aegean Meridian       data/documents + data/eval + the holdout rewrites (the original D7 negatives: 48 clean + 12)

Parts (the `source` and `slice` fields of every row say where it comes from, for per-slice reports):
  akryon_prompts / aegean_prompts / aegean_holdout / aegean_attacks   the existing labelled prompts, as judge cases
  gold_new      about 90 new cases written for this test: indirect questions, cross-language rewrites, numbers only,
                summaries, and hard negatives (invented figures, public look-alikes, same topic, no secret)
  entity_new    person, client and salary candidates built from Akryon's real employee and client lists, with
                look-alike words, public figures and numbers that are not pay as negatives (all new words)
  aug           label-preserving rewrites (Greeklish, capitals, no accents, typos) of about 20% of the rows above

Candidates are built like the brain would: the nearest registered chunk (the same 16 word chunker, both language
versions of each document registered). There is no embedding model here, so the nearest chunk is found by character
overlap (exact for a known source document) and the shown score is label-neutral, drawn from the same distribution
for YES and NO so it cannot give the answer away.
"""

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services" / "brain" / "src"))

import judge_aug  # noqa: E402
from brain.documents.chunking import chunk_text, language  # noqa: E402
from eval_judge import _cos, _grams, _words  # noqa: E402
from gen_finetune import FRAMES_EL, FRAMES_EN, REASONS, frame_for, shingles, to_row, toks, window, write_jsonl  # noqa: E402
from judge_format import doc_candidate, entity_candidate, reason_ok  # noqa: E402

SEED = 4242
AUG_SHARE = 0.20
OUT = ROOT / "data" / "finetune"
PROMPTS = ROOT / "data" / "eval" / "prompts.csv"
ATTACKS = ROOT / "data" / "eval" / "attacks.csv"
HOLDOUT = ROOT / "services" / "brain" / "tests" / "data" / "holdout.json"
AEG_DOCS = ROOT / "data" / "documents"

# ---------------------------------------------------------------- hand-written gold cases
# world "ak" = Akryon, "ag" = Aegean. per document: positives (text, slice, anchor) and negatives (text, slice)
GOLD: dict[tuple[str, str], dict] = {
    ("ak", "DOC-HR-003"): {
        "pos": [
            ("Ο μισθός ενός Senior στο επίπεδο L3 ξεκινά από 33 χιλιάδες και φτάνει τις 46 χιλιάδες ετησίως.", "paraphrase_same", "L3 Senior"),
            ("Level 5 heads of department are paid between 66,000 and 95,000 euros gross a year, with an average of 80,000.", "paraphrase_cross", "L5 Head"),
            ("Αυξήσεις 2027: προϋπολογισμός 4,5% (~400 χιλιάδες), βαθμός 5 παίρνει 7–9% και οι βαθμοί 1–2 τίποτα.", "summary_numbers", "Αυξήσεις 2027"),
            ("Σωστά θυμάμαι ότι εννέα στελέχη, μεταξύ τους τέσσερις senior Salesforce developers, θα πάρουν bonus παραμονής μέχρι 15.000;", "indirect_question", "Πρόγραμμα παραμονής"),
            ("The retention scheme caps total payments at 110,000 euros in two instalments, June and December 2027, and nobody is told before March.", "paraphrase_cross", "Πρόγραμμα παραμονής"),
            ("Gender pay gap 6.2% in 2026, target below 3% by 2028, 150k set aside for L2-L3 corrections.", "numbers_only", "Ισότητα αμοιβών"),
        ],
        "neg": [
            ("Πώς εξηγώ σε έναν υποψήφιο ότι το κλιμάκιο αποδοχών εξαρτάται από την εμπειρία χωρίς να δώσω αριθμούς;", "same_topic"),
            ("Write a generic policy paragraph on how annual bonuses are split between company and individual performance, with invented percentages.", "fictional_numbers"),
            ("Τι είναι το μη σταθμισμένο μισθολογικό χάσμα και πώς υπολογίζεται;", "same_topic"),
            ("According to Eurostat the unadjusted gender pay gap in the EU was around 12 percent. Add this to our public sustainability page.", "public_fact"),
            ("Φτιάξε πρότυπο επιστολής αποδοχών που δεν περιέχει ποσά, μόνο placeholders.", "same_topic"),
            ("What are common retention bonus structures for software engineers?", "same_topic"),
            ("Μετάφρασε στα αγγλικά: Ευχαριστούμε για τη συμμετοχή σας στη συνέντευξη, θα επικοινωνήσουμε σύντομα.", "generic"),
            ("Our marketing team takes next week off for the holiday, remind everyone to plan ahead.", "trap_similar_words"),
            ("Ποια επίπεδα seniority χρησιμοποιούν συνήθως οι εταιρείες συμβούλων τεχνολογίας, από L1 έως L5;", "same_topic"),
        ],
    },
    ("ak", "DOC-PROP-002"): {
        "pos": [
            ("Η τελική τιμή προς την Ερυδία είναι 2,38 εκατ. χωρίς ΦΠΑ μετά από έκπτωση 15% στην τιμή καταλόγου των 2,8.", "paraphrase_same", "Οικονομική προσφορά"),
            ("We will not go below 2.15 million for the bank, that is a 25 percent margin, and anything lower needs the CEO's approval.", "paraphrase_cross", "Κατώτατο όριο"),
            ("Στον δεύτερο γύρο οι προμήθειες της τράπεζας θα ζητήσουν άλλο 10% έκπτωση, γι' αυτό πρώτα υποχωρούμε στις δόσεις και μετά, αν χρειαστεί, δίνουμε τρεις μήνες hypercare δωρεάν.", "paraphrase_same", "Στρατηγική διαπραγμάτευσης"),
            ("The legacy CRM data is in bad shape, about eighteen percent duplicates, so we added forty days of cleanup that the client does not know about.", "paraphrase_cross", "Κίνδυνος"),
            ("Ερυδία: κόστος 1,62 εκατ., περιθώριο 32%, ανταγωνιστές στα 2,6 και 1,9 εκατ.", "summary_numbers", "Κόστος"),
            ("Η πληρωμή γίνεται σε τέσσερις δόσεις: 20% με την υπογραφή, 30% στο τέλος της ανάπτυξης, 30% μετά τη μεταφορά δεδομένων και 20% μετά την παραγωγική λειτουργία.", "copy_exact", "Οικονομική προσφορά"),
        ],
        "neg": [
            ("Πώς διαπραγματεύομαι με το τμήμα προμηθειών μιας τράπεζας όταν ζητά έκπτωση; Δώσε γενικές τακτικές.", "same_topic"),
            ("Estimate the effort in person-days for migrating a CRM with about a million records, using generic assumptions.", "same_topic"),
            ("Τι είναι το hypercare και πόσο διαρκεί συνήθως μετά από μια παραγωγική λειτουργία;", "same_topic"),
            ("Write a polite email to a bank thanking them for the meeting about a CRM project, no figures.", "same_topic"),
            ("Τι σημαίνει μικτό περιθώριο 30% σε ένα έργο λογισμικού; Εξήγησέ το με φανταστικό παράδειγμα.", "fictional_numbers"),
            ("List typical risks when migrating customer records between CRM systems, such as duplicates.", "same_topic"),
            ("Πώς γράφω ρήτρα πληρωμής σε δόσεις για ένα έργο πληροφορικής; Βάλε placeholders για τα ποσοστά.", "same_topic"),
            ("According to a retailer's public annual report it will open 85 new stores next year, summarise it.", "trap_same_number"),
            ("Ποια είναι η διαφορά ανάμεσα σε Salesforce Financial Services Cloud και Sales Cloud;", "public_fact"),
        ],
    },
    ("ak", "DOC-MEMO-001"): {
        "pos": [
            ("Θα προσφέρουμε 12 εκατ. για την Pyxida, 8,4 σε μετρητά και 3,6 ως earn-out με βάση το ARR.", "paraphrase_same", "Προσφερόμενο τίμημα"),
            ("The executive committee has approved up to 13.5 million euros for the Pyxida deal, but we never tell the sellers.", "paraphrase_cross", "Προσφερόμενο τίμημα"),
            ("Δύο ιδρυτές γράφουν σχεδόν όλο τον κώδικα, γι' αυτό σκεφτόμαστε πακέτο παραμονής 600 χιλιάδων για αυτούς και τέσσερις μηχανικούς για δύο χρόνια.", "paraphrase_same", "Εξάρτηση από τους δύο ιδρυτές"),
            ("Project Pegasus: acquire Pyxida Labs of Thessaloniki, 34 employees, revenue 4.1 million and EBITDA 0.9 million in 2025.", "paraphrase_cross", "Σύνοψη"),
            ("Πήγασος: due diligence Δεκ–Ιαν, υπογραφή 26/2, κλείσιμο 31/3, μη δεσμευτική προσφορά 20/11.", "summary_numbers", "Χρονοδιάγραμμα"),
            ("Ισχύει ότι το 45% των εσόδων της Pyxida έρχεται από τρεις πελάτες και ο κώδικας SAP θέλει 250.000 για εκσυγχρονισμό;", "indirect_question", "Κίνδυνοι"),
        ],
        "neg": [
            ("Πώς δομείται ένα earn-out σε μια εξαγορά εταιρείας λογισμικού; Εξήγησε γενικά.", "same_topic"),
            ("Write a checklist for the due diligence of a small software company, no company names.", "same_topic"),
            ("Τι είναι το ARR και πώς διαφέρει από τα συνολικά έσοδα;", "same_topic"),
            ("Summarise this public news item: a Greek software firm was acquired by a foreign group, financial terms were not disclosed.", "public_fact"),
            ("Πόσο διαρκεί συνήθως η ενσωμάτωση μιας εταιρείας μετά από εξαγορά;", "same_topic"),
            ("Draft a reminder that board materials are confidential and must not be pasted into AI tools.", "trap_similar_words"),
            ("Ποια είναι τα στάδια ενός M&A deal από τη μη δεσμευτική προσφορά ως το κλείσιμο;", "same_topic"),
            ("What is key-person risk in a startup and how is it usually mitigated?", "same_topic"),
            ("Φτιάξε πρόσκληση για συνεδρίαση της ομάδας στην αίθουσα συσκέψεων την Πέμπτη στις 09:00.", "trap_similar_words"),
        ],
    },
    ("ag", "salary-bands"): {
        "pos": [
            ("Ένας νέος σύμβουλος ξεκινά από 32.000 ευρώ και ένας διευθυντής έργων μπορεί να φτάσει τις 90.000.", "paraphrase_same", "Σύμβουλοι"),
            ("Developers in the third grade earn between 45 and 60 thousand euros a year, second grade 35 to 45.", "paraphrase_cross", "Προγραμματιστές"),
            ("Το μπόνους δεν ξεπερνά το 15% του βασικού και η μέση αύξηση του 2027 δεν θα ξεπεράσει το 4% της μισθοδοσίας.", "paraphrase_same", "Μπόνους και αυξήσεις"),
            ("In accounting salaries range from 26,000 to 55,000, and lawyers start at 35,000 and top out at 70,000.", "paraphrase_cross", "Λοιπά τμήματα"),
            ("Ρωτάω για κάποιον στο λογιστήριο: είναι σωστό ότι οι αποδοχές εκεί κυμαίνονται από 26 έως 55 χιλιάδες;", "indirect_question", "Λοιπά τμήματα"),
            ("Salary bands 2027: devs 28–60k, consultants 32k–90k, accounting 26–55k, legal 35–70k, bonus max 15%.", "summary_numbers", "Σύμβουλοι"),
        ],
        "neg": [
            ("Ποιο είναι το μέσο εισόδημα ενός προγραμματιστή στην Ελλάδα σύμφωνα με δημόσιες έρευνες;", "public_fact"),
            ("Draft an email to the team announcing that the annual salary review will take place in January.", "same_topic"),
            ("Πώς υπολογίζεται το ετήσιο μπόνους απόδοσης; Εξήγησε με φανταστικό μισθό 30.000 ευρώ και 10%.", "fictional_numbers"),
            ("What is a typical bonus cap in consulting firms?", "same_topic"),
            ("Γράψε αγγελία για νέο σύμβουλο χωρίς να αναφέρεις μισθό.", "same_topic"),
            ("Πώς λειτουργεί η μισθολογική κλίμακα σε έναν οργανισμό; Δώσε γενικό παράδειγμα με βαθμίδες Α, Β και Γ χωρίς αριθμούς.", "same_topic"),
            ("The new hire asks whether salary information is confidential at most companies, answer in general terms.", "same_topic"),
            ("Σε ποια εποχή του χρόνου συνήθως γίνονται οι αξιολογήσεις αποδοχών στις εταιρείες συμβούλων;", "same_topic"),
        ],
    },
    ("ag", "delphi-msa"): {
        "pos": [
            ("The fixed fee is 840,000 euros a year invoiced quarterly in advance; analysts cost 260 euros a day and senior consultants 410 outside scope.", "paraphrase_same", "Fees"),
            ("Η Delphi πληρώνει 840.000 ευρώ τον χρόνο σε τριμηνιαία προκαταβολή και οι επιπλέον εργασίες χρεώνονται 260 ευρώ ημερησίως για αναλυτή.", "paraphrase_cross", "Fees"),
            ("Our liability stops at twelve months of fees, except confidentiality breaches, fraud and wilful misconduct where there is no cap.", "paraphrase_same", "Liability"),
            ("Η διάρκεια είναι τρία χρόνια με αυτόματη ανανέωση ανά έτος, και μετά τον πρώτο χρόνο ο πελάτης μπορεί να φύγει με 90 ημέρες ειδοποίηση πληρώνοντας το μισό των υπολοίπων αμοιβών.", "paraphrase_cross", "Term"),
            ("If availability drops by half a percent below 99.5, the client gets a 5% credit on the quarterly fee, capped at 20%.", "paraphrase_same", "Service levels"),
            ("MSA Delphi: 840k fixed, 3-year term, 90 days notice, liability cap 12 months, breach notice within 24h.", "summary_numbers", "Term"),
        ],
        "neg": [
            ("What does a typical master services agreement contain?", "same_topic"),
            ("Εξήγησε τη διαφορά ανάμεσα σε ρήτρα περιορισμού ευθύνης και ρήτρα αποζημίωσης.", "same_topic"),
            ("Write a template data breach notification email with placeholders for dates and affected systems.", "same_topic"),
            ("Πόσο είναι συνήθως τα SLA διαθεσιμότητας για cloud υπηρεσίες; Δώσε παραδείγματα από δημόσιες σελίδες παρόχων.", "public_fact"),
            ("Summarise the GDPR rule that a processor must notify the controller of a personal data breach without undue delay.", "public_fact"),
            ("Draft a short note to a client confirming that quarterly invoices are sent on the first working day, no amounts.", "same_topic"),
            ("Τι σημαίνει αυτόματη ανανέωση συμβολαίου και πώς την αποφεύγω;", "same_topic"),
            ("Which courts have jurisdiction for disputes under Greek law contracts in general?", "same_topic"),
        ],
    },
    ("ag", "board-memo"): {
        "pos": [
            ("The plan is to open Sofia and Belgrade in Q2 2027 with four million euros from retained earnings and break even after twenty-two months.", "paraphrase_same", "opens offices in Sofia and Belgrade"),
            ("Θα αγοράσουμε τη Danube Advisory της Σόφιας με 1,5 εκατ. ευρώ· έχει 11 συμβούλους και οι ιδρυτές μένουν τρία χρόνια.", "paraphrase_cross", "acquire a small Sofia firm"),
            ("The sellers' exclusivity runs out on 15 April, so the board must decide before then; announcement to staff in the first week of May, Sofia opens 1 July.", "paraphrase_same", "final decision on the Danube Advisory offer"),
            ("Στο Βελιγράδι δεν αγοράζουμε τίποτα, θα νοικιάσουμε γραφείο, θα προσλάβουμε επικεφαλής χώρας έως τέλος Μαρτίου και ο πρώτος πελάτης είναι τηλεπικοινωνιακός πάροχος.", "paraphrase_cross", "In Serbia we do not intend to buy anything"),
            ("We expect to pay a 15 percent premium over local rates for senior consultants in Belgrade for two years because they are scarce.", "paraphrase_same", "hiring: senior consultants in Belgrade are scarce"),
            ("Balkans: 4M budget, Danube Advisory up to 1.5M, Belgrade 12 people in year one, vote in March.", "summary_numbers", "three things"),
        ],
        "neg": [
            ("How do consulting firms usually evaluate expansion into a new country?", "same_topic"),
            ("Εξήγησε τι είναι το break even και δώσε ένα φανταστικό παράδειγμα.", "fictional_numbers"),
            ("Write an announcement email to staff about a new office opening, with placeholders for city and date.", "same_topic"),
            ("Ποιες είναι οι πρακτικές για προσλήψεις senior στελεχών σε νέες αγορές;", "same_topic"),
            ("What is key person risk in small acquisitions?", "same_topic"),
            ("Summarise public information about Bulgaria's accession to the euro area.", "public_fact"),
            ("Πώς λειτουργεί ένα exclusivity period σε μια διαπραγμάτευση εξαγοράς;", "same_topic"),
            ("Compare the cost of renting offices in Sofia and Belgrade using public real estate reports.", "public_fact"),
        ],
    },
}

# ---------------------------------------------------------------- entity pools (new words, none used in training)
EL_FULL = ["Στο αίτημα εγκρίνει ο υπεύθυνος: {n}.", "Επόμενος ομιλητής στη συνάντηση: {n}.",
           "Παραλήπτης του πακέτου: {n}, γραφείο Μαρουσίου.", "Στείλε τις σημειώσεις στο όνομα {n} και σημείωσέ τες εμπιστευτικές.",
           "Συντάκτης της αναφοράς: {n}. Βελτίωσε τη διατύπωση."]
EN_FULL = ["The ticket was opened by {n} on Monday, please summarise the thread.", "Add {n} to the distribution list for the quarterly review.",
           "Reminder: {n} owns the migration checklist.", "Draft a thank you note to {n} for the great presentation."]
EL_SUR = ["Σημείωση για {n}: η συνάντηση μεταφέρθηκε στις 11:00.", "Ο φάκελος: {n}, να ενημερωθεί το HR."]
EN_SUR = ["Please loop in {n} before sending the offer.", "{n} signed off the budget yesterday."]
CLIENT_EL = ["Ετοίμασε το briefing για τη σύσκεψη με {c}.", "Γράψε ένα σύντομο email προς {c} για την αλλαγή ημερομηνίας."]
CLIENT_EN = ["The renewal discussion with {c} starts next month, draft the agenda.", "{c} asked for a revised timeline, write a reply."]
SAL_YES = [("el", "Ο L3 Senior Consultant αμείβεται με {x} ετησίως."), ("el", "Ο μισθός της διευθύντριας είναι {x} μικτά."),
           ("en", "The base pay for an L4 lead is {x} gross a year."), ("en", "Offer the candidate {x} and mention it is the band minimum.")]
AMOUNT_NO = [("en", "The migration plan covers {x} and ends in October.", ["1,200 users", "85 stores", "40 slides"]),
             ("en", "The server listens on {x}, update the firewall rule.", ["port 8443", "port 9090"]),
             ("en", "Upgrade to {x} before the demo, the release notes are online.", ["version 3.2", "version 5.1"]),
             ("en", "The attachment is {x}, compress it before sending.", ["2.5 GB", "480 MB"]),
             ("el", "Η συνάντηση ξεκινά στις {x} στην αίθουσα συσκέψεων.", ["09:00", "14:30", "17:15"]),
             ("el", "Η παρουσίαση έχει {x} και πρέπει να μικρύνει.", ["40 διαφάνειες", "55 διαφάνειες"]),
             ("el", "Το ticket {x} περιμένει έγκριση από την ομάδα υποστήριξης.", ["#48213", "#90377"])]
LOOKALIKE = [
    ("Cook", ["Cook the vegetables slowly and add the sauce at the end, write the steps for the canteen menu."]),
    ("Young", ["Young professionals prefer flexible hours, summarise the survey for the newsletter."]),
    ("Bell", ["Ring the Bell at the reception when the courier arrives, add it to the onboarding guide."]),
    ("Stone", ["Stone fruit like peaches and plums should be ordered for the summer event."]),
    ("Ford", ["The new Ford electric van arrives next month, update the fleet spreadsheet."]),
    ("Jordan", ["Our next regional conference is in Jordan in March, book the travel."]),
    ("Georgia", ["Compare the visa rules for Georgia and Armenia for business trips."]),
    ("Paris", ["The train to Paris leaves at dawn, adjust the itinerary."]),
    ("Chelsea", ["Chelsea played at home on Saturday, write a light intro for the football pool email."]),
    ("Hall", ["The Hall booking for the offsite is confirmed, send the floor plan."]),
    ("Park", ["The Park next to the office is closed for repairs, tell the team to use the other entrance."]),
    ("Rivers", ["Rivers in the north flooded last spring, explain how climate data is used in insurance models."]),
    ("Ρήγας", ["Ο Ρήγας ήταν ήρωας της ελληνικής επανάστασης και θέλω μια σύντομη περίληψη για μαθητές."]),
    ("Βλάχοι", ["Οι Βλάχοι της Πίνδου ζούσαν ως κτηνοτρόφοι, γράψε μια παράγραφο για τα ήθη τους."]),
    ("Παππάς", ["Ο Παππάς του χωριού έκανε τον αγιασμό, διόρθωσε το κείμενο."]),
    ("Δρόσος", ["Η Δρόσος του πρωινού βοηθά τα φυτά, μετάφρασε την πρόταση στα αγγλικά."]),
    ("Μαρούσι", ["Το Μαρούσι έχει πολλά γραφεία εταιρειών τεχνολογίας, φτιάξε ένα σύντομο κείμενο για τη γειτονιά."]),
    ("Ζερβός", ["Ο ζερβός αμυντικός έπαιξε εξαιρετικά, γράψε ένα σχόλιο για τον αγώνα."]),
]
PUBLIC_FIGURES = [
    ("Ρήγας Φεραίος", "Ο Ρήγας Φεραίος οραματίστηκε μια βαλκανική δημοκρατία, κάνε μια περίληψη."),
    ("Κολοκοτρώνης", "Ο Κολοκοτρώνης ήταν στρατηγός του 1821, ετοίμασε ένα σύντομο κείμενο για παρουσίαση."),
    ("Orville Wright", "Orville Wright flew the first powered aeroplane in 1903, explain it in two sentences."),
    ("Marie Curie", "Marie Curie won two Nobel prizes, add a fact box to the presentation."),
    ("Ada Lovelace", "Ada Lovelace is often called the first programmer, write a short intro for the workshop."),
    ("Καζαντζάκης", "Ο Καζαντζάκης έγραψε τον Ζορμπά, δώσε μου μια φράση για το εισαγωγικό σημείωμα."),
    ("Ελύτης", "Ο Ελύτης τιμήθηκε με Νόμπελ λογοτεχνίας, φτιάξε μια πρόταση για την εκδήλωση."),
]


# ---------------------------------------------------------------- worlds and retrieval
def clean_md(s: str) -> str:
    s = re.sub(r"^---.*?---", "", s, flags=re.S) if s.startswith("---") else s
    s = re.sub(r"[*#|]", " ", s)
    s = re.sub(r"^\s*-{3,}\s*$", " ", s, flags=re.M)
    return re.sub(r"[ \t]+", " ", s).strip()


def load_variant(title: str, sens: str, text: str) -> dict:
    chunks = chunk_text(clean_md(text))
    return {"title": title, "sens": sens, "lang": language(chunks[0]) if chunks else "en", "chunks": chunks,
            "text": clean_md(text),
            "grams": [_grams(c) for c in chunks]}


def aegean_world() -> dict[str, list[dict]]:
    world = {}
    for f in sorted(AEG_DOCS.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        _, front, body = raw.split("---", 2)
        title = re.search(r'title:\s*"?(.*?)"?\s*$', front, re.M).group(1)
        sens = re.search(r"sensitivity:\s*(\w+)", front).group(1)
        world[f.stem] = [load_variant(title, sens, body)]
    return world


def akryon_world(root: Path) -> dict[str, list[dict]]:
    world = {}
    for r in csv.DictReader((root / "documents" / "documents.csv").open(encoding="utf-8")):
        variants = []
        for suffix, tkey in (("el", "title_el"), ("en", "title_en")):
            f = root / "documents" / r[f"file_{suffix}"]
            if f.exists():
                variants.append(load_variant(r[tkey], r["sensitivity"], f.read_text(encoding="utf-8")))
        world[r["document_id"]] = variants
    return world


def nearest(world: dict, text: str, doc_id: str | None, anchor: str | None) -> tuple[dict, int]:
    best = (-1.0, None, 0)
    g = _grams(text)
    a = set(toks(anchor)) if anchor else None
    for d, variants in world.items():
        if doc_id and d != doc_id:
            continue
        for v in variants:
            for i, (c, cg) in enumerate(zip(v["chunks"], v["grams"], strict=True)):
                s = len(a & set(toks(c))) + 0.01 * _cos(g, cg) if a else _cos(g, cg)
                if s > best[0]:
                    best = (s, v, i)
    return best[1], best[2]


class Builder:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.rows: list[dict] = []

    def doc(self, world: dict, text: str, doc_id: str | None, gold: str, source: str, sl: str,
            anchor: str | None = None, **flags) -> None:
        v, i = nearest(world, text, doc_id, anchor)
        chunk = v["chunks"][i]
        pl, cl = language(text), language(chunk)
        shared = len(_words(text) & _words(chunk)) / max(1, len(_words(text) | _words(chunk)))
        if shared >= 0.5:
            kind, score = "copy", round(shared, 3)
        else:
            kind = "paraphrase"
            floor = 0.88 if pl == cl else 0.86
            score = min(0.96, max(floor, self.rng.gauss(0.90, 0.02)))  # same law for YES and NO
        cand = doc_candidate(v["title"], v["sens"], kind, score, pl, cl, chunk)
        reason = ("Reveals confidential content of the matched document." if gold == "YES"
                  else "No confidential content of the matched document is revealed.")
        self._add(text, cand, gold, reason, {"type": "doc_chunk", "source": source, "slice": sl, **flags})

    def entity(self, sentence: str, category: str, span: str, gold: str, key: str, source: str, sl: str,
               **flags) -> None:
        found = re.search(re.escape(span), sentence, re.I)
        if not found:
            raise SystemExit(f"span {span!r} not in {sentence!r}")
        span = found.group(0)
        cand = entity_candidate(category, span, window(sentence, span))
        self._add(sentence, cand, gold, self.rng.choice(REASONS[key]),
                  {"type": "entity", "category": category, "source": source, "slice": sl, **flags})

    def _add(self, prompt: str, cand: dict, gold: str, reason: str, meta: dict) -> None:
        assert reason_ok(reason), reason
        meta["sub"] = meta["slice"]
        self.rows.append({"prompt": prompt, "cand": cand, "verdict": gold, "reason": reason, "meta": meta})


# ---------------------------------------------------------------- the parts
NAME = re.compile(r"\b[A-ZΑ-Ω][a-zα-ωά-ώ]+(?:\s+[A-ZΑ-Ω][a-zα-ωά-ώ]+)+\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?:\+30[ .-]?)?69\d{2}[ .-]?\d{3}[ .-]?\d{3,4}")


def note_slice(notes: str) -> str:
    n = notes.lower()
    if "ίδιο θέμα" in n or "same topic" in n:
        return "same_topic"
    if "public" in n or "δημόσι" in n:
        return "public_doc"
    if "παγίδα" in n or "trap" in n or "checksum" in n or "dna" in n:
        return "trap"
    return "general"


def akryon_prompts(b: Builder, root: Path, world: dict, aliases: list[str]) -> None:
    for r in csv.DictReader((root / "eval" / "prompts.csv").open(encoding="utf-8")):
        text, lab, lt, doc = r["text"], r["label"], r["leak_type"], r["document_id"]
        if lab == "leak" and lt in {"copy", "edit", "paraphrase", "split"} and doc in world:
            b.doc(world, text, doc, "YES", "akryon_prompts", lt)
        elif lab == "clean":
            b.doc(world, text, None, "NO", "akryon_prompts", note_slice(r["notes"]), hard=True)
        ent = r["entity_types"]
        if lab == "leak" and lt == "pattern":
            if "CLIENT_NAME" in ent:
                al = next((a for a in aliases if a.lower() in text.lower()), None)
                if al:
                    b.entity(text, "CLIENT", al, "YES", "CLIENT_yes", "akryon_prompts", "client_name_prompt")
            elif "PERSON" in ent or "EMAIL" in ent or "PHONE" in ent:
                m = EMAIL.search(text) or PHONE.search(text) or NAME.search(text)
                if m:
                    cat = "PERSON" if NAME.fullmatch(m.group(0)) else "EMAIL" if EMAIL.fullmatch(m.group(0)) else "PHONE"
                    key = {"PERSON": "PERSON_yes", "EMAIL": "PERSON_yes", "PHONE": "PHONE_yes"}[cat]
                    b.entity(text, cat, m.group(0), "YES", key, "akryon_prompts", f"{cat.lower()}_prompt")


def public_copies(b: Builder, world: dict) -> None:
    """Quotes and partial copies of PUBLIC documents: sensitivity public means the answer is NO."""
    for doc, variants in sorted(world.items()):
        for v in variants:
            if v["sens"] != "public":
                continue
            sents = [s.strip() for s in re.split(r"(?<=[.;!?])\s+", v["text"]) if 8 <= len(s.split()) <= 40]
            for s in b.rng.sample(sents, min(8, len(sents))):
                b.doc(world, frame_for(b.rng, s), doc, "NO", "akryon_public", "public_doc_copy", hard=True)


def aegean_prompts(b: Builder, world: dict) -> None:
    rows = list(csv.DictReader(PROMPTS.open(encoding="utf-8")))
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    title_to_id = {v[0]["title"]: k for k, v in world.items()}
    for r in rows:
        if r["label"] == "leak" and r["document_id"] in world and r["leak_type"] in {"paraphrase", "edit", "copy", "split"}:
            b.doc(world, r["text"], r["document_id"], "YES", "aegean_prompts", r["leak_type"])
        elif r["label"] == "clean":
            b.doc(world, r["text"], None, "NO", "aegean_prompts", "clean", hard=True, d7_neg60=True)
        elif r["label"] == "leak" and "person_email_phone" in r["entity_types"]:
            m = EMAIL.search(r["text"]) or PHONE.search(r["text"]) or NAME.search(r["text"])
            if m:
                cat = "PERSON" if NAME.fullmatch(m.group(0)) else "EMAIL" if EMAIL.fullmatch(m.group(0)) else "PHONE"
                b.entity(r["text"], cat, m.group(0), "YES", "PHONE_yes" if cat == "PHONE" else "PERSON_yes",
                         "aegean_prompts", f"{cat.lower()}_prompt")
    for p in holdout["positives"]:
        b.doc(world, p["text"], title_to_id.get(p.get("doc", "")), "YES", "aegean_holdout", "paraphrase")
    for n in holdout["negatives"]:
        b.doc(world, n["text"], None, "NO", "aegean_holdout", "same_topic", hard=True, d7_neg60=True)
    for r in csv.DictReader(ATTACKS.open(encoding="utf-8")):
        if r["technique"] == "document_rewrite":
            b.doc(world, r["text"], None, "YES", "aegean_attacks", "paraphrase")
        elif r["technique"] == "clean":
            b.doc(world, r["text"], None, "NO", "aegean_attacks", "clean", hard=True)


def gold_cases(b: Builder, worlds: dict) -> None:
    for (w, doc), g in GOLD.items():
        if w not in worlds:
            continue
        for text, sl, anchor in g["pos"]:
            b.doc(worlds[w], text, doc, "YES", "gold_new", sl, anchor=anchor)
        for text, sl in g["neg"]:
            b.doc(worlds[w], text, doc, "NO", "gold_new", sl, hard=True)


def entity_cases(b: Builder, root: Path) -> list[str]:
    rng = b.rng
    emps = list(csv.DictReader((root / "org" / "employees.csv").open(encoding="utf-8")))
    clients = list(csv.DictReader((root / "clients.csv").open(encoding="utf-8")))
    aliases = sorted({a for c in clients for a in c["aliases"].split(";") if a}, key=lambda a: (-len(a), a))
    people = rng.sample(emps, 24)
    for i, e in enumerate(people[:12]):
        el = i % 2 == 0
        name = e["full_name"] if el else judge_aug.greeklish(e["full_name"])
        t = rng.choice(EL_FULL if el else EN_FULL).format(n=name)
        b.entity(t, "PERSON", name, "YES", "PERSON_yes", "entity_new", "person_full_name")
    for i, e in enumerate(people[12:]):
        el = i % 2 == 0
        name = e["last_name"] if el else judge_aug.greeklish(e["last_name"])
        t = rng.choice(EL_SUR if el else EN_SUR).format(n=name)
        b.entity(t, "PERSON", name, "YES", "PERSON_yes", "entity_new", "person_surname_only")
    for c in rng.sample(aliases, 12):
        t = rng.choice(CLIENT_EL if language(c) == "el" else CLIENT_EN).format(c=c)
        b.entity(t, "CLIENT", c, "YES", "CLIENT_yes", "entity_new", "client_name")
    for _ in range(12):
        lang, t = rng.choice(SAL_YES)
        v = rng.randint(16, 95) * 1000
        x = f"{v:,}".replace(",", ".") + " ευρώ" if lang == "el" else f"€{v:,}"
        b.entity(t.format(x=x), "AMOUNT", x, "YES", "AMOUNT_yes", "entity_new", "salary_figure")
    for span, sents in LOOKALIKE:
        for s in sents:
            b.entity(s, "PERSON", span, "NO", "PERSON_no", "entity_new", "lookalike_word", hard=True)
    for span, s in PUBLIC_FIGURES:
        b.entity(s, "PERSON", span, "NO", "PUBLIC_no", "entity_new", "public_figure", hard=True)
    for _lang, t, xs in AMOUNT_NO:
        for x in xs:
            b.entity(t.format(x=x), "AMOUNT", x, "NO", "AMOUNT_no", "entity_new", "number_not_salary", hard=True)
    return aliases


def augment_rows(rows: list[dict], rng: random.Random) -> list[dict]:
    out = []
    for gold in ("YES", "NO"):
        pool = [e for e in rows if e["verdict"] == gold and e["meta"]["source"] != "aug"]
        for i, e in enumerate(rng.sample(pool, round(len(pool) * AUG_SHARE))):
            kinds = judge_aug.KINDS_ENTITY if e["cand"]["type"] == "entity" else judge_aug.KINDS_DOC
            for k in range(len(kinds)):
                a = judge_aug.augment(e, kinds[(i + k) % len(kinds)], rng, language)
                if a:
                    a["meta"].pop("d7_neg60", None)  # the 60 are the originals only
                    a["meta"]["parent_source"] = e["meta"]["source"]
                    a["meta"]["source"] = "aug"
                    a["meta"]["slice"] = "aug_" + a["meta"]["aug"]
                    out.append(a)
                    break
    return out


# ---------------------------------------------------------------- checks and stats
def strip_frame(p: str) -> str:
    """Without the shared wrapper ("Can you tidy this up? ...") only the sentence is compared."""
    for f in FRAMES_EL + FRAMES_EN:
        prefix = f.split("{t}")[0].strip()
        if prefix and p.startswith(prefix):
            return p[len(prefix):].strip()
    return p


def train_prompts() -> tuple[set, set]:
    shing, spans = set(), set()
    for name in ("train.jsonl", "val.jsonl"):
        f = OUT / name
        if not f.exists():
            raise SystemExit(f"{f} missing: run scripts/gen_finetune.py first (the overlap check needs it)")
        for line in f.open(encoding="utf-8"):
            row = json.loads(line)
            user = row["messages"][0]["content"]
            prompt = user.split("PROMPT:\n", 1)[1].split("\n\nCANDIDATE:", 1)[0]
            cand = json.loads(user.split("CANDIDATE:\n", 1)[1])
            shing |= shingles(strip_frame(prompt), 6)
            if cand.get("category") in ("PERSON", "CLIENT") and " " in cand.get("span", "").strip():
                spans.add(" ".join(toks(cand["span"])))
    return shing, spans


def check(rows: list[dict]) -> list[str]:
    shing, spans = train_prompts()
    problems = []
    for e in rows:
        if shingles(strip_frame(e["prompt"]), 6) & shing:
            problems.append("6-word overlap with training data: " + e["prompt"][:70])
        if e["cand"].get("category") in ("PERSON", "CLIENT") and " ".join(toks(e["cand"].get("span", ""))) in spans:
            problems.append("entity span also in training data: " + e["cand"]["span"])
    return problems


def stats_md(rows: list[dict], have_akryon: bool) -> str:
    n = len(rows)
    yes = sum(r["verdict"] == "YES" for r in rows)
    greek = sum(language(r["prompt"]) == "el" for r in rows)
    d7 = sum(bool(r["meta"].get("d7_neg60")) for r in rows)

    def table(title: str, key) -> list[str]:
        c: Counter = Counter((key(r), r["verdict"]) for r in rows)
        keys = sorted({k for k, _ in c}, key=str)
        out = [f"### {title}", "", "| value | YES | NO | total |", "|---|---|---|---|"]
        out += [f"| {k} | {c[(k, 'YES')]} | {c[(k, 'NO')]} | {c[(k, 'YES')] + c[(k, 'NO')]} |" for k in keys]
        return out + [""]

    lines = [
        "# Test set for the D7 judge", "",
        "Made by `scripts/gen_judge_test.py` (seed 4242). **Never trained on**: no 6-word run, document, client or "
        "multi-word person name is shared with `train.jsonl` / `val.jsonl` (the script stops otherwise).", "",
        f"- Rows: **{n}**; YES {yes} ({yes / n:.0%}), NO {n - yes}; Greek prompts {greek} ({greek / n:.0%})",
        f"- Original D7 negatives (48 clean + 12 same-topic, the 60 the 42 false positives were measured on): **{d7}** (`d7_neg60`)",
        f"- Akryon pack included: **{'yes' if have_akryon else 'NO (run with --akryon; the Akryon parts are missing)'}**",
        "- Candidates use the nearest chunk by character overlap and a label-neutral score (same distribution for YES and NO)", "",
    ]
    lines += table("By source", lambda r: r["meta"]["source"])
    lines += table("By candidate type", lambda r: r["meta"]["type"])
    lines += table("By slice", lambda r: r["meta"]["slice"])
    lines += table("By language of the prompt", lambda r: language(r["prompt"]))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--akryon", type=Path, default=os.environ.get("AKRYON_DIR"),
                    help="the `data` folder of the Akryon mock data (documents/, eval/, org/, clients.csv)")
    args = ap.parse_args()
    rng = random.Random(SEED)
    b = Builder(rng)
    worlds = {"ag": aegean_world()}
    aliases: list[str] = []
    have_akryon = bool(args.akryon and Path(args.akryon, "documents", "documents.csv").exists())
    if have_akryon:
        root = Path(args.akryon)
        worlds["ak"] = akryon_world(root)
        aliases = entity_cases(b, root)
        akryon_prompts(b, root, worlds["ak"], aliases)
        public_copies(b, worlds["ak"])
    else:
        print("warning: no Akryon data given, building the eval-company parts only", file=sys.stderr)
    aegean_prompts(b, worlds["ag"])
    gold_cases(b, worlds)

    seen, rows = set(), []
    for e in b.rows:  # exact duplicates out
        k = (e["prompt"], json.dumps(e["cand"], ensure_ascii=False, sort_keys=True))
        if k not in seen:
            seen.add(k)
            rows.append(e)
    rows += augment_rows(rows, rng)
    rng.shuffle(rows)
    problems = check(rows)
    if problems:
        print("\n".join(sorted(set(problems))[:30]), file=sys.stderr)
        sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "test.jsonl", [to_row(e) for e in rows])
    (OUT / "test_stats.md").write_text(stats_md(rows, have_akryon), encoding="utf-8")
    yes = sum(e["verdict"] == "YES" for e in rows)
    print(f"test.jsonl: {len(rows)} rows, YES {yes}, NO {len(rows) - yes}")


if __name__ == "__main__":
    main()
