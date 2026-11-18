"""Build the fine-tune set for the D7 borderline judge (gemma3:1b LoRA on Kaggle).

Run:  python3 scripts/gen_finetune.py            (standard library only, fixed seed, same output every time)
      python3 scripts/gen_finetune.py --avoid /path/to/other/test/data   (extra folders the training data must not touch)

Reads  data/train_org/   the invented TRAINING company (Taygetos Oils SA). Never the eval company.
Writes data/finetune/{train,val}.jsonl and data/finetune/stats.md

Every example is one borderline candidate (see judge_format.py) with a YES/NO answer:
  doc_chunk  a matched chunk of a registered document, with the prompt that matched it
  entity     a possible person, client, salary figure or phone number with its context
The chunks are cut by the brain's own chunker (16 word windows), so the judge sees what the brain would send.

Guards that stop the script (exit 1) instead of writing bad data:
  - no 6-word run of any prompt or chunk appears in data/eval, data/documents, data/org or --avoid folders
  - no full person name, client or company of those folders is used
  - about 30% YES, at least 50% hard negatives, at least 40% Greek prompts, reasons of 12 words or less with no digits
"""

import argparse
import csv
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "services" / "brain" / "src"))

from brain.documents.chunking import chunk_text, language  # noqa: E402
import judge_aug  # noqa: E402
from judge_format import (  # noqa: E402
    build_input,
    build_output,
    doc_candidate,
    entity_candidate,
    gemma_text,
    reason_ok,
)

SEED = 42
YES_SHARE = 0.30
VAL_SHARE = 0.15
PRIORITY_SUBS = ("client_name", "surname_only")  # kept first when positives must be cut to hold 30/70
PRIORITY_CAP = 40
AUG_SHARE = 0.25  # share of each split rewritten as Greeklish, capitals, no accents or typos (same label)
TARGET_TOTAL = 1000
TRAIN_ORG = ROOT / "data" / "train_org"
OUT = ROOT / "data" / "finetune"
DEFAULT_AVOID = [ROOT / "data" / "eval", ROOT / "data" / "documents", ROOT / "data" / "org"]
# Surnames so common that two invented companies can share them. Only the full name must differ.
ALLOWED_SURNAME_OVERLAP = {"papadaki", "dimou", "kalli"}

DOCS = {  # key: (file, short name used in reasons)
    "sal": ("salary-bands-2028.md", "salary bands"),
    "nord": ("nordmarkt-supply-agreement.md", "Nordmarkt agreement"),
    "board": ("board-memo-bottling-plant.md", "bottling plant memo"),
    "price": ("pricing-engine.py", "pricing engine code"),
    "hr": ("hr-file-sideri.md", "HR personnel file"),
    "strat": ("strategy-deck-2028.md", "strategy deck"),
    "plist": ("export-price-list-2028.md", "export price list"),
    "pub": ("newsletter-harvest-2028.md", "public newsletter"),
    "pub2": ("visitor-shop-info.md", "public visitor page"),
}

# (doc, anchor in the document, [2 same-language rewrites], [2 other-language rewrites],
#  summary with numbers, [2 same-topic questions that leak nothing, 1 in the other language])
FACTS = [
    ("sal", "εργάτες παραγωγής της πρώτης βαθμίδας",
     ["Στην πρώτη βαθμίδα ένας εργάτης παραγωγής παίρνει περίπου είκοσι δύο χιλιάρικα τον χρόνο, ενώ στη δεύτερη είκοσι έξι.",
      "Ο ετήσιος μισθός των εργατών παραγωγής είναι 22 χιλιάδες στην πρώτη κατηγορία και 26 χιλιάδες στη δεύτερη."],
     ["Production workers in the first grade earn about twenty-two thousand euros a year and in the second grade twenty-six thousand.",
      "Grade one factory staff are paid 22k euros annually, grade two 26k."],
     "Συνοψίζοντας: οι εργάτες μας βγάζουν 22 με 26 χιλιάδες τον χρόνο ανάλογα με τη βαθμίδα.",
     ["Πώς καθορίζεται γενικά η βαθμίδα ενός εργάτη παραγωγής σε μια βιομηχανία τροφίμων;",
      "Γράψε μια αγγελία για εργάτη παραγωγής σε μονάδα ελαιολάδου χωρίς να αναφέρεις μισθό.",
      "What is the legal minimum wage rule for factory workers in Greece?"]),
    ("sal", "χημικοί τροφίμων και οι υπεύθυνοι ποιότητας",
     ["Για χημικούς τροφίμων και υπεύθυνους ποιότητας το εύρος αποδοχών είναι 32.000 έως 45.000 ευρώ τον χρόνο.",
      "Όσοι δουλεύουν ως χημικοί τροφίμων ή στον ποιοτικό έλεγχο παίρνουν από τριάντα δύο μέχρι σαράντα πέντε χιλιάδες ετησίως."],
     ["Food chemists and quality managers are paid between 32,000 and 45,000 euros per year.",
      "The pay range for quality managers and food chemists runs from thirty-two to forty-five thousand."],
     "Η κλίμακα για ποιότητα και χημικούς είναι 32 έως 45 χιλιάδες.",
     ["Ποια προσόντα χρειάζεται ένας χημικός τροφίμων για να δουλέψει σε ελαιουργείο;",
      "Φτιάξε ερωτήσεις συνέντευξης για υπεύθυνο ποιότητας.",
      "What does a quality manager do in a food company?"]),
    ("sal", "διευθυντής εξαγωγών έχει πάγιο μισθό",
     ["Ο επικεφαλής των εξαγωγών έχει σταθερό μισθό 68 χιλιάδες και μπόνους μέχρι 15% στις πωλήσεις εκτός ΕΕ.",
      "Η αμοιβή του διευθυντή εξαγωγών είναι εξήντα οκτώ χιλιάδες το χρόνο συν προμήθεια δεκαπέντε τοις εκατό για πωλήσεις εκτός Ευρώπης."],
     ["The export director gets a base salary of 68,000 euros plus up to 15 percent bonus on non-EU sales.",
      "Our head of exports earns sixty-eight thousand fixed, with a fifteen percent bonus outside the EU."],
     "Ο διευθυντής εξαγωγών: 68Κ πάγιο και έως 15% μπόνους.",
     ["Πώς σχεδιάζεται συνήθως ένα σχήμα μπόνους για διευθυντή εξαγωγών;",
      "Γράψε περιγραφή θέσης για διευθυντή εξαγωγών ελαιολάδου.",
      "How do export bonuses usually work in food companies?"]),
    ("sal", "ετήσια αύξηση για το 2028",
     ["Το 2028 όλοι παίρνουν αύξηση 3%, μόνο οι εργάτες παραγωγής παίρνουν 5%.",
      "Οι αυξήσεις του επόμενου έτους είναι τρία τοις εκατό γενικά και πέντε για τους εργάτες στην παραγωγή."],
     ["Next year's raise is three percent for everyone, except production workers who get five percent.",
      "For 2028 pay rises are capped at 3 percent, with 5 percent only for factory workers."],
     "Αυξήσεις 2028: 3% όλοι, 5% οι εργάτες.",
     ["Τι ποσοστό πληθωρισμού να λαμβάνω υπόψη όταν σχεδιάζω αυξήσεις γενικά;",
      "Πώς ανακοινώνω σε μια ομάδα ότι φέτος δεν θα υπάρξουν αυξήσεις;",
      "Draft a polite email explaining that annual raises are reviewed in January."]),
    ("sal", "επίδομα συγκομιδής",
     ["Υπάρχει ένα επίδομα συγκομιδής 400 ευρώ τον μήνα από Νοέμβριο μέχρι Ιανουάριο που δεν γράφεται στα συμβόλαια.",
      "Στη συγκομιδή δίνουμε ανεπίσημα τετρακόσια ευρώ μηνιαίως τους χειμερινούς μήνες."],
     ["During the harvest from November to January we pay a four hundred euro monthly allowance that is not written in the contracts.",
      "There is an unofficial harvest bonus of 400 euros a month in winter."],
     "Επίδομα συγκομιδής 400€/μήνα Νοέμβριο–Ιανουάριο, εκτός συμβάσεων.",
     ["Τι είναι το επίδομα εποχικής εργασίας στην Ελλάδα και ποιοι το δικαιούνται;",
      "Γράψε ανακοίνωση για την έναρξη της συγκομιδής προς τους εργαζόμενους.",
      "What is a seasonal allowance in employment law?"]),

    ("nord", "commits to buy at least one hundred and eighty thousand litres",
     ["Nordmarkt must take a minimum of 180,000 litres of extra virgin oil each year at 7.10 euros a litre.",
      "The German buyer is obliged to purchase at least one hundred eighty thousand litres annually, fixed at seven euros ten per litre."],
     ["Η Nordmarkt δεσμεύεται να αγοράζει τουλάχιστον 180.000 λίτρα έξτρα παρθένο ελαιόλαδο τον χρόνο προς 7,10 ευρώ το λίτρο.",
      "Ο Γερμανός πελάτης παίρνει κάθε χρόνο τουλάχιστον εκατόν ογδόντα χιλιάδες λίτρα με σταθερή τιμή επτά ευρώ και δέκα λεπτά."],
     "Summary: Nordmarkt buys 180k litres a year at 7.10.",
     ["What should a minimum purchase commitment clause normally include in a supply contract?",
      "Explain what a fixed price clause is.",
      "Τι σημαίνει ρήτρα ελάχιστης αγοράς σε σύμβαση προμήθειας;"]),
    ("nord", "grants Nordmarkt exclusivity",
     ["We gave Nordmarkt sole retail distribution rights in Germany and Austria for three years and cannot sell to rival chains there.",
      "For three years no competing supermarket chain in Germany or Austria can be supplied by us because Nordmarkt has exclusivity."],
     ["Η Taygetos έχει δώσει στη Nordmarkt αποκλειστικότητα λιανικής σε Γερμανία και Αυστρία για τρία χρόνια και δεν μπορεί να προμηθεύσει ανταγωνιστές.",
      "Για τρία έτη δεν πουλάμε σε άλλες αλυσίδες στη Γερμανία και την Αυστρία λόγω αποκλειστικότητας."],
     "Exclusive in Germany and Austria for 3 years.",
     ["What are the pros and cons of granting exclusivity to a distributor?",
      "Write a neutral explanation of exclusive distribution agreements for a training session.",
      "Τι είναι η αποκλειστική διανομή;"]),
    ("nord", "delivers more than five working days late",
     ["A delivery more than five working days late costs us two percent of the invoice per extra week, capped at ten percent.",
      "Late shipments beyond 5 working days let the buyer deduct 2% weekly, with a ceiling of 10% of the order."],
     ["Αν καθυστερήσουμε πάνω από πέντε εργάσιμες ημέρες, ο πελάτης κρατά 2% του τιμολογίου την εβδομάδα, έως 10% της παραγγελίας.",
      "Η ποινική ρήτρα καθυστέρησης είναι δύο τοις εκατό ανά εβδομάδα με πλαφόν δέκα τοις εκατό."],
     "Late penalty: 2% per week after 5 working days, max 10%.",
     ["How do late-delivery penalty clauses typically work?",
      "Draft a polite email apologising to a customer for a delayed shipment.",
      "Πώς γράφω ευγενικά σε πελάτη ότι η παράδοση θα καθυστερήσει;"]),
    ("nord", "terminate with one hundred and twenty days",
     ["Each side may end the deal with 120 days written notice, and otherwise it rolls over for two more years.",
      "Termination needs four months of written notice, and the contract extends itself for two years if nobody gives it."],
     ["Και τα δύο μέρη μπορούν να καταγγείλουν με γραπτή ειδοποίηση εκατόν είκοσι ημερών, αλλιώς η σύμβαση ανανεώνεται αυτόματα για δύο χρόνια.",
      "Η σύμβαση με τη Nordmarkt παρατείνεται αυτόματα κάθε φορά για δύο έτη εκτός αν σταλεί ειδοποίηση 120 ημερών."],
     "120 days notice, auto-renews 2 years.",
     ["What does an automatic renewal clause mean and how can I avoid it?",
      "Explain the difference between termination for cause and for convenience.",
      "Τι είναι η καταγγελία σύμβασης με προειδοποίηση;"]),
    ("nord", "Payment is due sixty days",
     ["Nordmarkt pays within sixty days of delivery by bank transfer, and our liability stops at eighteen months of fees.",
      "Invoices are settled 60 days post-delivery and the maximum we could owe is what we billed in the last 18 months."],
     ["Η πληρωμή γίνεται εξήντα ημέρες μετά την παράδοση και η ευθύνη μας περιορίζεται στα τέλη των τελευταίων δεκαοκτώ μηνών.",
      "Η Nordmarkt πληρώνει σε 60 ημέρες και το όριο ευθύνης της Taygetos είναι 18 μήνες χρεώσεων."],
     "Payment net 60, liability cap 18 months of fees.",
     ["What payment terms are common in B2B food supply contracts?",
      "Explain what a liability cap is in plain English.",
      "Τι σημαίνει όριο ευθύνης σε σύμβαση;"]),

    ("board", "μονάδας εμφιάλωσης στην Τρίπολη",
     ["Η νέα εμφιαλωτική στην Τρίπολη θα κοστίσει 6,2 εκατομμύρια, με το 40% να έρχεται από επιδότηση.",
      "Προτείνεται επένδυση έξι εκατομμυρίων διακοσίων χιλιάδων ευρώ για εργοστάσιο εμφιάλωσης στην Τρίπολη, με σαράντα τοις εκατό επιδότηση."],
     ["We propose building a bottling plant in Tripoli for a total investment of 6.2 million euros, 40 percent covered by a subsidy.",
      "The new Tripoli bottling facility costs six point two million, forty percent funded by grants."],
     "Εμφιάλωση Τρίπολη: 6,2 εκ. €, 40% επιδότηση.",
     ["Ποιες επιδοτήσεις υπάρχουν γενικά για επενδύσεις σε μονάδες τροφίμων στην Ελλάδα;",
      "Πώς γράφω ένα υπόμνημα επένδυσης προς διοικητικό συμβούλιο;",
      "What are typical steps to build a bottling plant?"]),
    ("board", "απόσβεση της επένδυσης",
     ["Υπολογίζουμε ότι η επένδυση θα αποσβεστεί σε πέντε χρόνια και θα βγάζουμε δύο εκατομμύρια φιάλες ετησίως.",
      "Η δυναμικότητα θα φτάσει τα 2 εκατ. φιάλες τον χρόνο και η επιστροφή του κεφαλαίου αναμένεται σε 5 έτη."],
     ["Payback is estimated at five years and capacity will reach two million bottles a year.",
      "The plant will produce 2 million bottles annually and pay for itself in five years."],
     "Απόσβεση 5 έτη, 2 εκατ. φιάλες.",
     ["Πώς υπολογίζεται η περίοδος απόσβεσης μιας επένδυσης;",
      "Εξήγησε τη διαφορά μεταξύ δυναμικότητας και παραγωγής σε μια μονάδα.",
      "How is payback period calculated?"]),
    ("board", "εξαγορά του ανταγωνιστή Μεσσηνιακή Ελιά",
     ["Θα ξεκινήσουμε τον Μάρτιο συζητήσεις για να αγοράσουμε τη Μεσσηνιακή Ελιά με πλαφόν προσφοράς τέσσερα εκατομμύρια που μένει κρυφό.",
      "Το ανώτατο ποσό για την Μεσσηνιακή Ελιά είναι 4 εκατ. ευρώ και δεν θα το πούμε σε κανέναν."],
     ["Negotiations to acquire our competitor Messiniaki Elia start in March with a secret maximum bid of four million euros.",
      "We will bid up to 4 million for Messiniaki Elia and keep it confidential."],
     "Εξαγορά Μεσσηνιακής Ελιάς: ξεκινά Μάρτιο, ανώτατη προσφορά 4 εκατ.",
     ["Ποια είναι τα στάδια μιας εξαγοράς εταιρείας γενικά;",
      "Τι είναι το due diligence;",
      "How do companies value a small competitor before acquiring it?"]),
    ("board", "ανακοίνωση προς τους εργαζόμενους",
     ["Δεν θα πούμε τίποτα στο προσωπικό πριν την υπογραφή, γιατί η παλιά γραμμή κλείνει και χάνονται 14 θέσεις.",
      "Οι εργαζόμενοι θα ενημερωθούν μετά τις υπογραφές· η παλιά γραμμή παραγωγής κλείνει και κόβονται δεκατέσσερις θέσεις."],
     ["Staff will only be told after signing because the old line closes and fourteen jobs are cut.",
      "We keep the closure of the old line and the loss of 14 positions from employees until the deal is signed."],
     "Κλείνει η παλιά γραμμή, 14 θέσεις περικόπτονται, σιωπή μέχρι την υπογραφή.",
     ["Πώς ανακοινώνεται σωστά μια αναδιάρθρωση στο προσωπικό;",
      "Τι ορίζει το ελληνικό δίκαιο για τις ομαδικές απολύσεις γενικά;",
      "How should a company communicate layoffs respectfully?"]),
    ("board", "απόφαση του συμβουλίου θα ληφθεί",
     ["Το ΔΣ θα αποφασίσει στις 20 Φεβρουαρίου και θα πάρουμε δάνειο από την Τράπεζα Πελοποννήσου.",
      "Στη συνεδρίαση της εικοστής Φεβρουαρίου ψηφίζεται το σχέδιο, με χρηματοδότηση από την Τράπεζα Πελοποννήσου."],
     ["The board will decide on 20 February and the financing will come from a loan from Peloponnese Bank.",
      "The vote takes place at the February 20 meeting and Peloponnese Bank will lend the funds."],
     "ΔΣ 20 Φεβρουαρίου, δάνειο Τράπεζα Πελοποννήσου.",
     ["Πώς προετοιμάζομαι για μια συνεδρίαση διοικητικού συμβουλίου;",
      "Τι πρέπει να περιέχει μια πρόταση χρηματοδότησης προς τράπεζα;",
      "What does a board of directors usually vote on?"]),

    ("price", "BASE_COST_PER_LITRE = 3.85",
     ["Set BASE_COST_PER_LITRE to 3.85 and TARGET_MARGIN to 0.46, so the quote is cost divided by one minus the margin.",
      "We compute price as 3.85 divided by (1 minus 0.46), the 46 percent margin applies to every retail chain."],
     ["Το βασικό κόστος ανά λίτρο είναι 3,85 ευρώ και ο στόχος περιθωρίου 46%, οπότε η τιμή = κόστος / (1 - 0,46).",
      "Στον κώδικα ορίζουμε BASE_COST_PER_LITRE 3.85 και TARGET_MARGIN 0.46 για τις προσφορές."],
     "Pricing code: cost 3.85 per litre, margin 0.46.",
     ["Write a Python function that computes selling price from cost and a target margin.",
      "How do I calculate gross margin versus markup?",
      "Γράψε συνάρτηση Python που υπολογίζει τιμή πώλησης από κόστος και περιθώριο."]),
    ("price", "def volume_discount(litres: int)",
     ["def volume_discount(litres: int) -> float: returns 0.115 when litres are at least 180000, 0.07 from 60000, otherwise zero.",
      "Discount function: 11.5% off at 180,000 litres and above (Nordmarkt tier), 7% at 60,000 litres, nothing below."],
     ["Η volume_discount δίνει έκπτωση 11,5% από 180.000 λίτρα, 7% από 60.000 λίτρα και μηδέν κάτω από αυτά.",
      "Οι κλίμακες έκπτωσης όγκου: 0.115 για 180000+ λίτρα, 0.07 για 60000+."],
     "Tiers: 180k litres 11.5%, 60k litres 7%.",
     ["Write a Python function for tiered volume discounts with three example tiers of my choice.",
      "What is a typical volume discount structure in B2B sales?",
      "Πώς υλοποιώ κλιμακωτή έκπτωση όγκου σε Python;"]),
    ("price", "Export to Germany carries a 9 percent premium",
     ["In quote(), price is multiplied by 1.09 for germany and 1.14 for gulf, so those are the export premiums.",
      "Quotes for German buyers get a 9% uplift and Gulf buyers 14% on the base price."],
     ["Στη quote() η τιμή πολλαπλασιάζεται επί 1,09 για Γερμανία και 1,14 για Κόλπο· αυτά είναι τα premium εξαγωγών.",
      "Οι Γερμανοί πελάτες χρεώνονται 9% πάνω και οι χώρες του Κόλπου 14%."],
     "Premium: Germany +9%, Gulf +14%.",
     ["How do I add a channel-specific markup to a Python pricing function?",
      "What is a pricing premium in export markets?",
      "Τι είναι το premium τιμής στις εξαγωγές;"]),
    ("price", "def floor_price(channel: str)",
     ["floor_price returns cost times 1.22 rounded to two decimals, but for gulf it is a hard 5.40.",
      "The lowest price sales can accept is 3.85 × 1.22 except Gulf where it is fixed at 5.40 euros."],
     ["Η floor_price επιστρέφει κόστος επί 1,22 και για τον Κόλπο σταθερά 5,40 ευρώ.",
      "Η κατώτατη τιμή που δέχεται η πώληση είναι κόστος επί 1.22, με εξαίρεση τον Κόλπο στα 5,40."],
     "Floor price: cost x 1.22, Gulf fixed 5.40.",
     ["What is a price floor and why do sales teams use it?",
      "Write a unit test for a function that rounds prices to two decimals.",
      "Πώς γράφω unit test για συνάρτηση τιμολόγησης;"]),
    ("price", "we never quote below this margin",
     ["The 46 percent margin is a hard rule: no quote to a retail chain may go below it.",
      "TARGET_MARGIN of 0.46 is the minimum we ever accept when quoting a supermarket chain."],
     ["Το περιθώριο 46% είναι απόλυτος κανόνας: καμία προσφορά σε αλυσίδα λιανικής δεν πέφτει κάτω από αυτό.",
      "Δεν δίνουμε ποτέ τιμή σε σούπερ μάρκετ με περιθώριο μικρότερο του 0.46."],
     "Rule: min margin 46% for retail chains.",
     ["What margin do supermarkets typically expect from suppliers?",
      "How can I explain gross margin to a new sales hire?",
      "Τι περιθώριο κέρδους θεωρείται υγιές στα τρόφιμα;"]),

    ("hr", "γραπτή προειδοποίηση τον Σεπτέμβριο",
     ["Ο Σιδέρη πήρε γραπτή επίπληξη τον Σεπτέμβριο επειδή έλειψε τρεις φορές από τη βάρδια συγκομιδής χωρίς λόγο.",
      "Για τρεις αδικαιολόγητες απουσίες στη συγκομιδή ο επόπτης Πάνος Σιδέρη έχει ήδη γραπτή προειδοποίηση."],
     ["Panos Sideri received a written warning in September for three unexcused absences from the harvest shift.",
      "The production supervisor was formally warned in writing for missing the harvest shift three times."],
     "Σιδέρη: γραπτή προειδοποίηση Σεπτέμβριο, 3 απουσίες.",
     ["Πώς γράφω μια γραπτή προειδοποίηση για αδικαιολόγητες απουσίες γενικά;",
      "Τι προβλέπει ο νόμος για τις αδικαιολόγητες απουσίες εργαζομένου;",
      "How should a manager document repeated absences?"]),
    ("hr", "μισθός του είναι τριάντα έξι χιλιάδες",
     ["Ο επόπτης παίρνει 36.000 ευρώ τον χρόνο και η περσινή του αξιολόγηση βγήκε «κάτω από τις προσδοκίες».",
      "Με μισθό τριάντα έξι χιλιάδες ετησίως, ο Πάνος είχε φέτος αξιολόγηση που δεν κάλυψε τις προσδοκίες."],
     ["His salary is 36,000 euros a year and last year's review was below expectations.",
      "The supervisor earns thirty-six thousand and his latest appraisal rated him under expectations."],
     "Σιδέρη: 36Κ μισθός, αξιολόγηση κάτω από προσδοκίες.",
     ["Πώς δίνω εποικοδομητική αξιολόγηση σε εργαζόμενο που υπολείπεται των στόχων;",
      "Φτιάξε πρότυπο φόρμας αξιολόγησης προσωπικού.",
      "What is a performance improvement plan?"]),
    ("hr", "Άργυρω Μαυρογένη, υπεύθυνη ποιότητας, κατέγραψε",
     ["Η υπεύθυνη ποιότητας κατέγραψε δύο φορές ότι ο επόπτης έπαιξε τον έλεγχο οξύτητας πριν την εμφιάλωση.",
      "Δύο περιστατικά παράκαμψης του ελέγχου οξύτητας από τον Σιδέρη έχουν καταγραφεί από την Μαυρογένη."],
     ["The quality manager logged two incidents where the supervisor skipped the acidity check before bottling.",
      "Mavrogeni recorded Sideri bypassing the acidity test twice."],
     "2 περιστατικά παράκαμψης ελέγχου οξύτητας από τον επόπτη.",
     ["Γιατί είναι σημαντικός ο έλεγχος οξύτητας στο ελαιόλαδο;",
      "Πώς διερευνώ ένα περιστατικό ποιότητας σε εργοστάσιο τροφίμων;",
      "What is acidity in olive oil grading?"]),
    ("hr", "εξετάζει απόλυση με αποζημίωση",
     ["Αν υπάρξει και τρίτο περιστατικό, εξετάζεται απόλυση με οκτώ μηνιαίους μισθούς αποζημίωση.",
      "Το τμήμα προσωπικού σκέφτεται να τον απολύσει με οκτώ μισθούς αποζημίωση σε περίπτωση τρίτης παράβασης."],
     ["HR is considering dismissal with eight months of severance if a third incident is confirmed.",
      "A third incident would lead to termination with an eight month severance payment."],
     "Πιθανή απόλυση με 8 μισθούς αν υπάρξει τρίτο περιστατικό.",
     ["Πώς υπολογίζεται η νόμιμη αποζημίωση απόλυσης στην Ελλάδα;",
      "Ποια είναι τα βήματα μιας νόμιμης απόλυσης;",
      "What is severance pay?"]),
    ("hr", "αίτημα για ιατρική άδεια",
     ["Έχει ζητήσει ιατρική άδεια λόγω προβλήματος στη μέση και δεν έχει αποφασιστεί ακόμη.",
      "Το αίτημα του εργαζομένου για άδεια λόγω μέσης εκκρεμεί στο τμήμα ανθρώπινου δυναμικού."],
     ["He has requested medical leave for a back problem and the decision is pending.",
      "A medical leave request for a lower back condition is still waiting for HR to decide."],
     "Εκκρεμεί ιατρική άδεια για πρόβλημα μέσης.",
     ["Πώς διαχειρίζεται ένα τμήμα HR αιτήματα ιατρικής άδειας γενικά;",
      "Τι δικαιώματα έχει ο εργαζόμενος σε ασθενειακή άδεια;",
      "What medical information may an employer ask for?"]),

    ("strat", "grow revenue from forty-one million",
     ["We want revenue to rise from 41 to 56 million euros in 2028, led by Germany and the Gulf.",
      "The plan is to take sales from forty-one million to fifty-six million next year via German and Gulf growth."],
     ["Θέλουμε να αυξήσουμε τον τζίρο από 41 σε 56 εκατομμύρια το 2028, κυρίως με Γερμανία και Κόλπο.",
      "Ο στόχος για το 2028 είναι έσοδα πενήντα έξι εκατομμύρια από σαράντα ένα, με έμφαση στις αγορές Γερμανίας και Κόλπου."],
     "Revenue 41M to 56M in 2028 via Germany and Gulf.",
     ["How do I write a growth strategy section for a food exporter?",
      "What are growth levers for olive oil exporters in general?",
      "Πώς θέτω στόχους ανάπτυξης για μια εξαγωγική εταιρεία;"]),
    ("strat", "gross margin target is forty-six percent",
     ["Margin goal is 46%, and in March list prices go up 6 percent but distributors will not be warned.",
      "We aim for a 46 percent gross margin and will quietly lift prices six percent in March."],
     ["Στόχος μικτού περιθωρίου 46% και αύξηση τιμών 6% τον Μάρτιο χωρίς προειδοποίηση στους διανομείς.",
      "Θα ανεβάσουμε τις τιμές καταλόγου κατά έξι τοις εκατό τον Μάρτιο, αθόρυβα."],
     "Margin 46%, +6% price rise in March, no notice.",
     ["How should a company announce a price increase to distributors?",
      "What is a gross margin target?",
      "Πώς ενημερώνω πελάτες για αύξηση τιμών;"]),
    ("strat", "private label contract with Evripos Supermarkets",
     ["Evripos Supermarkets' private label deal is up for renewal and we would rather lose it than go under our floor price.",
      "We are ready to walk away from the Evripos private label contract instead of cutting our price below the floor."],
     ["Η σύμβαση ιδιωτικής ετικέτας με τα Evripos Supermarkets λήγει και προτιμάμε να τη χάσουμε παρά να πέσουμε κάτω από την κατώτατη τιμή.",
      "Δεν θα μειώσουμε την τιμή στη Evripos κάτω από το όριο, ακόμη κι αν χαθεί η σύμβαση."],
     "Evripos private label: renew only above floor price.",
     ["What are the risks and benefits of private label contracts for a producer?",
      "How do suppliers negotiate with supermarket chains in general?",
      "Τι είναι η ιδιωτική ετικέτα στα σούπερ μάρκετ;"]),
    ("strat", "hire a Dubai sales lead",
     ["A Dubai sales lead will be hired on 90k euros and a small warehouse there should open by September.",
      "We will recruit someone in Dubai at ninety thousand euros a year and have a warehouse ready by September."],
     ["Θα προσλάβουμε υπεύθυνο πωλήσεων στο Ντουμπάι με πακέτο 90 χιλιάδες ευρώ και αποθήκη έως τον Σεπτέμβριο.",
      "Ο νέος πωλητής του Ντουμπάι θα παίρνει ενενήντα χιλιάδες ευρώ και θα ανοίξουμε μικρή αποθήκη τον Σεπτέμβριο."],
     "Dubai sales lead at 90k, warehouse by September.",
     ["What should I consider before opening a warehouse in the Gulf?",
      "Write a job ad for a regional sales lead without salary details.",
      "Τι χρειάζεται για να ανοίξει εταιρεία γραφείο στο Ντουμπάι;"]),
    ("strat", "main risk is the harvest",
     ["Our biggest risk is a bad harvest, which would cut supply by a third and force costly purchases of Spanish oil.",
      "A poor olive season could take a third of our supply and make us import from Spain at higher cost."],
     ["Ο μεγαλύτερος κίνδυνος είναι η συγκομιδή: μια κακή χρονιά μειώνει την προσφορά κατά το ένα τρίτο και αναγκαζόμαστε να αγοράσουμε ελαιόλαδο από την Ισπανία.",
      "Μια κακή σοδειά θα μας στερήσει το ένα τρίτο της παραγωγής και θα φέρει ακριβότερες αγορές από Ισπανία."],
     "Harvest risk: supply -33%, buy from Spain.",
     ["How does a poor olive harvest usually affect olive oil prices in the market?",
      "What risk factors should a food exporter list in a strategy?",
      "Πώς επηρεάζει ο καιρός τη συγκομιδή ελιάς;"]),

    ("plist", "έξτρα παρθένο ελαιόλαδο των πέντε λίτρων",
     ["Το δοχείο των πέντε λίτρων έξτρα παρθένου πωλείται στις γερμανικές αλυσίδες προς 38 ευρώ.",
      "Οι μεγάλοι πελάτες στη Γερμανία πληρώνουν τριάντα οκτώ ευρώ για το δοχείο πέντε λίτρων."],
     ["The five litre can of extra virgin oil is priced at 38 euros for large customers in Germany.",
      "Big German buyers pay thirty-eight euros per 5 litre tin."],
     "5L έξτρα παρθένο: 38€ για Γερμανία.",
     ["Πόσο κοστίζει περίπου ένα δοχείο ελαιολάδου πέντε λίτρων στα σούπερ μάρκετ γενικά;",
      "Πώς συγκρίνω τιμές ελαιολάδου μεταξύ προμηθευτών;",
      "What affects the retail price of olive oil?"]),
    ("plist", "Baltic Delikatessen ισχύει ειδική έκπτωση",
     ["Η Baltic Delikatessen παίρνει 12% έκπτωση όταν παραγγέλνει πάνω από πενήντα παλέτες.",
      "Ειδική έκπτωση δώδεκα τοις εκατό για τη Baltic όταν η παραγγελία ξεπερνά τις 50 παλέτες."],
     ["Baltic Delikatessen gets a special 12 percent discount on orders above fifty pallets.",
      "Our Baltic client receives twelve percent off for orders over 50 pallets."],
     "Baltic: 12% έκπτωση πάνω από 50 παλέτες.",
     ["Πώς διαπραγματεύομαι έκπτωση όγκου με έναν προμηθευτή γενικά;",
      "Τι είναι η παλέτα και πόσα κιβώτια χωράει συνήθως;",
      "How do volume discounts work for distributors?"]),
    ("plist", "βιολογικά προϊόντα είναι είκοσι τοις εκατό",
     ["Τα βιολογικά κοστίζουν 20% παραπάνω από τα συμβατικά και δεν προσφέρονται σε μεταπωλητές.",
      "Η τιμή των βιολογικών είναι κατά ένα πέμπτο υψηλότερη και δεν πωλούνται σε ενδιάμεσους."],
     ["Organic products are priced twenty percent above conventional ones and are not offered to resellers.",
      "Organic costs 20% more than regular oil and resellers cannot buy it."],
     "Βιολογικά +20%, όχι σε μεταπωλητές.",
     ["Γιατί τα βιολογικά προϊόντα είναι συνήθως ακριβότερα;",
      "Τι πιστοποιήσεις χρειάζεται το βιολογικό ελαιόλαδο;",
      "What is the difference between organic and conventional olive oil?"]),
    ("plist", "κατώτατη τιμή που μπορεί να δεχτεί ο πωλητής",
     ["Ο πωλητής δεν επιτρέπεται να κατέβει κάτω από 4,80 το λίτρο χωρίς έγκριση.",
      "Η ελάχιστη τιμή που δέχεται χωρίς άδεια ο πωλητής είναι τέσσερα και ογδόντα ανά λίτρο."],
     ["A salesperson may not accept less than 4.80 euros per litre without approval.",
      "The floor price sales can take without sign-off is four euros eighty a litre."],
     "Floor: 4,80€/λίτρο.",
     ["Τι είναι η κατώτατη τιμή πώλησης και γιατί υπάρχει;",
      "Πώς εγκρίνεται μια έκπτωση εκτός πολιτικής σε μια εταιρεία;",
      "What approval levels are typical for discounts?"]),
    ("plist", "πελατών της Μέσης Ανατολής",
     ["Οι πελάτες Μέσης Ανατολής δίνουν 30% προκαταβολή και το υπόλοιπο πριν φορτωθεί το εμπόρευμα.",
      "Για τη Μέση Ανατολή ζητάμε τριάντα τοις εκατό από πριν και την υπόλοιπη πληρωμή πριν τη φόρτωση."],
     ["Middle East customers pay 30 percent upfront and the balance before loading.",
      "For Gulf buyers we take a thirty percent deposit and the rest before shipment."],
     "ME: 30% προκαταβολή, υπόλοιπο πριν φόρτωση.",
     ["Ποιοι τρόποι πληρωμής είναι ασφαλείς στις εξαγωγές γενικά;",
      "Τι είναι το ενέγγυο ακρεδητίβο (letter of credit);",
      "What payment terms reduce export risk?"]),
]


# Two more same-topic questions per fact (document language, other language), in FACTS order.
EXTRA_SAFE = [
    ["Υπολόγισε το κόστος εργοδότη για έναν εργάτη με μικτό μισθό που θα μου δώσω εγώ ως παράδειγμα.", "How do payroll taxes work for factory workers in Greece?"],
    ["Ποιες πιστοποιήσεις κάνουν έναν χημικό τροφίμων πιο ελκυστικό στην αγορά εργασίας;", "List typical responsibilities of a food chemist."],
    ["Πώς διαπραγματεύομαι πακέτο αμοιβών για διευθυντική θέση χωρίς να αναφέρω αριθμούς της εταιρείας μου;", "Explain what a base salary plus commission structure is."],
    ["Φτιάξε πρότυπο email προς το προσωπικό για την ετήσια αξιολόγηση αποδοχών.", "What percentage raise is generally considered fair in Europe?"],
    ["Πώς λειτουργούν τα εποχικά επιδόματα για συγκομιδή σε αγροτικές επιχειρήσεις γενικά;", "Write a thank-you note to seasonal harvest workers."],
    ["Give me a checklist for reviewing a supply agreement before signing.", "Τι είναι η ρήτρα take-or-pay;"],
    ["Summarise the legal concept of exclusive territory in distribution law.", "Ποιοι κίνδυνοι υπάρχουν όταν δίνεις αποκλειστικότητα σε έναν πελάτη;"],
    ["Write a template clause for liquidated damages without any real numbers.", "Εξήγησε τι είναι οι ρήτρες καθυστέρησης στις συμβάσεις προμήθειας."],
    ["What is the usual notice period for ending a distribution agreement in the EU?", "Πώς καταγγέλλεται μια σύμβαση αορίστου χρόνου;"],
    ["Draft an email asking a customer to settle an invoice that is two weeks overdue.", "Τι σημαίνει πληρωμή net 30 σε ένα τιμολόγιο;"],
    ["Εξήγησέ μου τι είναι το ΕΣΠΑ και πώς μπορεί να χρηματοδοτήσει μια βιομηχανική επένδυση.", "What permits does a bottling plant need in Greece?"],
    ["Ποιοι δείκτες χρησιμοποιούνται για να αξιολογηθεί μια επένδυση, εκτός από την απόσβεση;", "Explain NPV and IRR with a simple fictional example."],
    ["Τι να προσέξω όταν σκέφτομαι να αγοράσω μια μικρότερη εταιρεία του κλάδου μου;", "Write a confidentiality reminder for a negotiation team without naming any deal."],
    ["Πώς γράφω ανακοίνωση για την αλλαγή οργάνωσης σε μια γραμμή παραγωγής χωρίς λεπτομέρειες;", "What rights do employees have when a production line closes in the EU?"],
    ["Φτιάξε ημερήσια διάταξη για μια συνεδρίαση του διοικητικού συμβουλίου.", "What is the quorum rule for a board meeting?"],
    ["Refactor this function so the margin comes from a config file instead of a constant.", "Πώς ορίζω σταθερές ρύθμισης σε ένα Python module;"],
    ["Add type hints and docstrings to a function that returns a discount rate from a quantity.", "Τι διαφορά έχει το if/elif από το match στην Python;"],
    ["Write pytest cases for a quote function that has a channel argument.", "Πώς στρογγυλοποιώ τιμές σε δύο δεκαδικά στην Python;"],
    ["Explain why a floor price check should raise an error instead of silently returning a number.", "Πώς γράφω καθαρό κώδικα για κανόνες τιμολόγησης;"],
    ["Show how to validate that a margin is between zero and one in Python.", "Τι σημαίνει margin of safety σε τιμολόγηση;"],
    ["Φτιάξε πρότυπο πρακτικού συνάντησης για πειθαρχικό συμβούλιο χωρίς ονόματα.", "How do I write a neutral incident report?"],
    ["Δώσε μου παραδείγματα στόχων που μπορεί να έχει ένας επόπτης παραγωγής σε εργοστάσιο τροφίμων.", "What are fair criteria for a performance appraisal?"],
    ["Ποιες είναι οι σωστές διαδικασίες ελέγχου οξύτητας στο εργοστάσιο ελαιολάδου;", "How do audits of food production lines usually work?"],
    ["Ποια είναι τα δικαιώματα του εργαζομένου πριν από μια απόλυση στην Ελλάδα;", "Explain notice and severance rules for dismissal in general terms."],
    ["Πώς γράφω ευγενικά μια απάντηση σε αίτημα άδειας που εγκρίνεται;", "What is the difference between sick leave and medical leave?"],
    ["Help me outline a three-year growth plan for a food business using made-up numbers.", "Πώς φτιάχνω στόχους πωλήσεων ανά αγορά;"],
    ["How do I explain a pricing policy to a sales team in a motivating way?", "Τι είναι το μικτό περιθώριο και πώς διαφέρει από το καθαρό;"],
    ["List negotiation tactics for dealing with a large supermarket buyer.", "Πώς συμπεριφέρομαι όταν ένας πελάτης ζητά διαρκώς χαμηλότερες τιμές;"],
    ["Write a job ad for a sales lead based in the Gulf region, no pay details.", "Τι πρέπει να ξέρω για τη μισθοδοσία σε χώρες του Κόλπου;"],
    ["How can an olive oil producer protect itself against a bad harvest year?", "Ποιες ασφαλιστικές λύσεις υπάρχουν για αγροτικές καλλιέργειες;"],
    ["Φτιάξε πίνακα με τα μεγέθη συσκευασίας ελαιολάδου που βρίσκονται συνήθως στην αγορά.", "How should I present a price list to a new customer?"],
    ["Πώς γράφω ένα ευγενικό email που προσφέρει έκπτωση σε μεγάλη παραγγελία χωρίς να αναφέρω ποσοστά;", "What is a loyalty discount?"],
    ["Τι σημαίνει βιολογική πιστοποίηση και πώς ελέγχεται;", "Why do organic products cost more in general?"],
    ["Πώς δίνει έγκριση ένας προϊστάμενος για έκπτωση εκτός πολιτικής;", "How do I teach new salespeople to avoid discounting too early?"],
    ["Ποιους κινδύνους έχει η πληρωμή με προκαταβολή σε διεθνείς πωλήσεις;", "What is a documentary collection in export finance?"],
]
assert len(EXTRA_SAFE) == 35



# The one PUBLIC document: whatever is said about it is fine (sensitivity public), so every answer is NO.
PUBLIC_FACTS = [
    ("φετινή συγκομιδή ξεκινά την πρώτη εβδομάδα",
     ["Φέτος ο τρύγος της ελιάς αρχίζει στις αρχές Νοεμβρίου και κάθε Σάββατο το ελαιουργείο ανοίγει για τους επισκέπτες.",
      "Το ελαιουργείο δέχεται επισκέψεις τα Σάββατα και η συγκομιδή ξεκινά την πρώτη βδομάδα του Νοεμβρίου.",
      "The harvest starts in the first week of November and visitors are welcome at the mill every Saturday."]),
    ("πιστοποίηση ISO 22000",
     ["Έχουμε πιστοποίηση ISO 22000 και ανεβάζουμε στο site τις αναλύσεις κάθε παρτίδας.",
      "Η ασφάλεια τροφίμων πιστοποιήθηκε με ISO 22000 και τα αποτελέσματα κάθε παρτίδας είναι δημόσια.",
      "The company is ISO 22000 certified and publishes the lab results of each batch on its website."]),
    ("ετήσια γιορτή ελιάς στην Καλαμάτα",
     ["Η ετήσια γιορτή ελιάς γίνεται στις 12 Δεκεμβρίου στην Καλαμάτα, με γευσιγνωσία και ξεναγήσεις.",
      "Στις 12 Δεκεμβρίου στην Καλαμάτα έχει γιορτή ελιάς με δωρεάν γευσιγνωσία και περιήγηση στο εργοστάσιο.",
      "The annual olive festival takes place in Kalamata on 12 December with free tastings and mill tours."]),
    ("πρόγραμμα βιωσιμότητας",
     ["Ο πυρήνας της ελιάς γίνεται βιοκαύσιμο και θέλουμε να κόψουμε το νερό που καταναλώνουμε κατά το ένα τρίτο μέχρι το 2030.",
      "Στο πρόγραμμα βιωσιμότητας ο πυρήνας ανακυκλώνεται ως καύσιμο και η χρήση νερού μειώνεται κατά 33% έως το 2030.",
      "Olive pits are reused as biofuel and water use falls by a third by 2030 under the sustainability programme."]),
    ("εξυπηρέτηση πελατών απαντά καθημερινά",
     ["Η εξυπηρέτηση πελατών απαντά κάθε μέρα 9 με 5 στο τηλέφωνο και στη φόρμα του site.",
      "Οι καταναλωτές μπορούν να καλούν ή να γράφουν στο site από τις 9 το πρωί έως τις 5 το απόγευμα καθημερινά.",
      "Customer service answers every day from nine to five by phone and through the website form."]),
]

PUBLIC_FACTS2 = [
    ("welcomes visitors to the Kalamata mill",
     ["Visitors can come to the mill in Kalamata every day except Sunday and join a tasting at eleven or at four.",
      "The Kalamata mill is open Monday to Saturday and offers guided tastings twice a day, in the morning and in the afternoon.",
      "Το ελαιουργείο στην Καλαμάτα δέχεται επισκέπτες από Δευτέρα έως Σάββατο με ξεναγήσεις και γευσιγνωσία δύο φορές την ημέρα."]),
    ("Orders from our online shop ship within two working days",
     ["Online orders leave our warehouse within two working days, and shipping inside Greece costs nothing above sixty euros.",
      "If you order from the web shop it ships in two working days and delivery in Greece is free when the basket is over 60 euros.",
      "Οι παραγγελίες από το ηλεκτρονικό κατάστημα αποστέλλονται σε δύο εργάσιμες και η παράδοση στην Ελλάδα είναι δωρεάν πάνω από εξήντα ευρώ."]),
    ("Unopened bottles can be returned",
     ["You can send back bottles that were never opened within two weeks of delivery and get all your money back.",
      "Our return policy: unopened bottles, fourteen days from delivery, full refund.",
      "Μπορείτε να επιστρέψετε ανοιχτά μη χρησιμοποιημένα μπουκάλια μέσα σε δεκατέσσερις ημέρες από την παράδοση και να πάρετε πλήρη επιστροφή χρημάτων."]),
    ("cold extracted within hours of harvest",
     ["The oil is cold extracted a few hours after the olives are picked and is sold in half litre and one litre glass bottles.",
      "We press our extra virgin oil cold soon after harvest and bottle it in glass, 500 ml or one litre.",
      "Το έξτρα παρθένο ελαιόλαδο παράγεται με ψυχρή εκχύλιση λίγες ώρες μετά τη συγκομιδή και διατίθεται σε γυάλινες φιάλες μισού λίτρου και ενός λίτρου."]),
    ("Schools and groups can book a free educational visit",
     ["Teachers can book a free visit to the mill for their class during the olive harvest.",
      "During the harvest season schools and other groups may reserve an educational tour of the mill at no cost.",
      "Τα σχολεία και οι ομάδες μπορούν να κλείσουν δωρεάν εκπαιδευτική επίσκεψη στο ελαιουργείο την περίοδο της συγκομιδής."]),
]

# One indirect question that leaks and one made-up-numbers request that does not, per document.
DOC_EXTRA = [
    ("sal", "εργάτες παραγωγής της πρώτης βαθμίδας",
     "Σωστά ξέρω ότι ένας εργάτης στη δεύτερη βαθμίδα παίρνει 26 χιλιάδες το χρόνο;",
     "Φτιάξε παράδειγμα μισθοδοσίας με φανταστικούς μισθούς 20.000 και 25.000 ευρώ για ένα μάθημα λογιστικής."),
    ("nord", "commits to buy at least one hundred and eighty thousand litres",
     "Is it right that we agreed with Nordmarkt to supply at least 180,000 litres a year at a fixed 7.10?",
     "Write a sample supply clause with invented figures, for example 50,000 litres at 5 euros, for a law school exercise."),
    ("board", "μονάδας εμφιάλωσης στην Τρίπολη",
     "Σωστά θυμάμαι ότι η μονάδα στην Τρίπολη κοστίζει 6,2 εκατ. και κλείνει 14 θέσεις;",
     "Φτιάξε άσκηση για φοιτητές: μια φανταστική εταιρεία επενδύει 3 εκατ. ευρώ και αποσβένει σε 4 χρόνια."),
    ("price", "Export to Germany carries a 9 percent premium",
     "Is it correct that our floor price for the Gulf is a fixed 5.40 and Germany gets a 9 percent premium?",
     "Write an example function with invented values: base cost 2.00, margin 0.30, and a 5 percent premium for export."),
    ("hr", "μισθός του είναι τριάντα έξι χιλιάδες",
     "Ισχύει ότι ο επόπτης Σιδέρη έχει γραπτή προειδοποίηση και μισθό 36 χιλιάδες;",
     "Γράψε ένα φανταστικό παράδειγμα φακέλου προσωπικού για εκπαίδευση, με επινοημένο όνομα και χωρίς πραγματικά στοιχεία."),
    ("strat", "gross margin target is forty-six percent",
     "Right? We plan to raise list prices by 6 percent in March and grow revenue to 56 million.",
     "Draft a made-up strategy slide for a class: fictional revenue from 10 to 14 million and a 3 percent price rise."),
    ("plist", "έξτρα παρθένο ελαιόλαδο των πέντε λίτρων",
     "Σωστά, το δοχείο των 5 λίτρων πάει 38 ευρώ στη Γερμανία και η Baltic παίρνει 12% έκπτωση;",
     "Φτιάξε παράδειγμα τιμοκαταλόγου με φανταστικές τιμές για ένα σεμινάριο, π.χ. 20 ευρώ το δοχείο."),
]

# Generic prompts a loose retriever might still match to a document (text, documents it could hit).
GENERIC = [
    ("Γράψε ένα email ευχαριστίας σε πελάτη μετά από μια επιτυχημένη παράδοση.", ["nord", "plist"]),
    ("Draft a one-page template for onboarding a new factory worker.", ["sal", "hr"]),
    ("What is the statutory notice period for dismissing an employee in Greece?", ["hr", "sal"]),
    ("Εξήγησε τι είναι ο ΕΦΚΑ και πώς πληρώνονται οι εισφορές.", ["sal", "hr"]),
    ("Summarise the main points of the GDPR for a small food business.", ["hr", "nord"]),
    ("Translate into Greek: Our olive oil is cold pressed within four hours of harvest.", ["plist", "strat"]),
    ("What is the VAT rate on food in Greece?", ["plist", "price"]),
    ("Ποια είναι η νόμιμη αμοιβή για υπερωρία στην Ελλάδα;", ["sal", "hr"]),
    ("How do I politely ask my manager for a raise?", ["sal", "hr"]),
    ("Τι είναι ο όρος Incoterms FOB και πότε χρησιμοποιείται;", ["nord", "plist"]),
    ("Write a polite reminder for an overdue invoice.", ["nord", "plist"]),
    ("Βοήθησέ με να γράψω περιγραφή για τη θέση του πωλητή εξαγωγών.", ["sal", "strat"]),
    ("Compare Koroneiki and Arbequina olive varieties.", ["plist", "strat"]),
    ("Create a SWOT analysis template for a small exporter.", ["strat", "board"]),
    ("Τι σημαίνει ESG και γιατί ενδιαφέρει τις εταιρείες τροφίμων;", ["strat", "board"]),
    ("Give me five icebreakers for a team meeting.", ["hr", "strat"]),
    ("How long does olive oil stay fresh after bottling?", ["plist", "board"]),
    ("Ποιες είναι οι υποχρεώσεις ενός εργοδότη για την ασφάλεια στην εργασία;", ["hr", "board"]),
    ("Explain EBITDA in simple terms.", ["board", "strat"]),
    ("Write a function to convert litres to kilograms of olive oil.", ["price", "plist"]),
    ("Πώς υπολογίζω ΦΠΑ σε τιμή προϊόντος με Python;", ["price", "plist"]),
    ("What does a data processing agreement cover?", ["nord", "hr"]),
    ("Τι ξεχωρίζει μια ΕΠΕ από μια ΑΕ;", ["board", "strat"]),
    ("Write a LinkedIn post celebrating that our harvest season is starting.", ["strat", "sal"]),
    ("Suggest names for a new line of organic olive oil gift boxes.", ["plist", "strat"]),
    ("Τι διαφορά έχει το πρώτο από το δεύτερο πάτημα στο ελαιόλαδο;", ["plist", "board"]),
    ("What is the average salary of a food chemist in Europe according to public surveys?", ["sal", "hr"]),
    ("Πόσες ώρες την εβδομάδα είναι το νόμιμο ωράριο εργασίας στην Ελλάδα;", ["sal", "hr"]),
    ("Summarise this public press release: the EU approved new olive oil labelling rules effective next year.", ["plist", "strat"]),
    ("Make a checklist for visiting a customer's factory.", ["nord", "board"]),
    ("Ποιες είναι οι πρακτικές καλής διαχείρισης αποθήκης;", ["board", "strat"]),
    ("How do I handle a customer who complains about oil quality?", ["plist", "hr"]),
    ("Εξήγησε με παράδειγμα πώς φαίνεται ο ΦΠΑ σε ένα τιμολόγιο.", ["price", "plist"]),
    ("Please check these dates: shipment on 12 March, invoice on 30 March, payment on 29 May.", ["nord", "plist"]),
    ("Add up 40 pallets, 12 cases and 380 litres for the packing list.", ["plist", "nord"]),
    ("ISO 22000 certification takes about six months, what are the steps?", ["hr", "board"]),
    ("Τι χρειάζεται για πιστοποίηση ISO 22000;", ["hr", "board"]),
    ("Η παραγγελία 4521 έχει 36 κιβώτια και 2 παλέτες· φτιάξε πίνακα.", ["plist", "nord"]),
    ("What are the standard working hours rules in Germany?", ["hr", "sal"]),
]

GENERIC += [
    ("Πώς συντάσσω πρόσκληση για το χριστουγεννιάτικο δείπνο της εταιρείας;", ["hr", "strat"]),
    ("Summarise the key changes in EU packaging waste rules for food producers.", ["plist", "board"]),
    ("Τι είναι το ΓΕΜΗ και τι πληροφορίες είναι δημόσιες;", ["board", "strat"]),
    ("Write a short bio for a new head of quality, using placeholders for the name.", ["hr", "sal"]),
    ("Πόσες μέρες ετήσιας άδειας δικαιούται ένας εργαζόμενος στην Ελλάδα;", ["hr", "sal"]),
    ("Explain the difference between gross and net salary using a made-up example.", ["sal", "hr"]),
    ("Πώς κάνω αναγωγή ευρώ σε δολάριο με Python;", ["price", "plist"]),
    ("What are the main incoterms for sea freight?", ["nord", "plist"]),
    ("Τι είναι η εγγύηση καλής εκτέλεσης;", ["nord", "board"]),
    ("Create a weekly production schedule template for a bottling line.", ["board", "price"]),
    ("Εξήγησε τι είναι το ισοζύγιο και πώς διαβάζεται.", ["board", "strat"]),
    ("How do I congratulate a colleague on a work anniversary?", ["hr", "sal"]),
    ("Ποια είναι τα στάδια διαδικασίας πρόσληψης σε μια μεσαία επιχείρηση;", ["hr", "sal"]),
    ("Draft a press release about our participation in a public food fair.", ["strat", "plist"]),
    ("Τι χρειάζεται για εξαγωγή τροφίμων εκτός ΕΕ;", ["plist", "strat"]),
    ("What is a purchase order and what fields does it contain?", ["nord", "plist"]),
    ("Εξήγησε τη διαφορά μεταξύ προϋπολογισμού και πρόβλεψης.", ["strat", "board"]),
    ("Write a regex that matches a Greek postal code.", ["price", "plist"]),
    ("Πώς ορίζεται ο υπερωριακός μισθός σε βάρδια Σαββάτου;", ["sal", "hr"]),
    ("Suggest agenda points for an annual supplier review meeting.", ["nord", "strat"]),
    ("Ποιες είναι οι βασικές αρχές του HACCP;", ["hr", "board"]),
    ("How is olive oil graded as extra virgin according to EU rules?", ["plist", "hr"]),
    ("Μετάφρασε στα αγγλικά: Η συγκομιδή ξεκίνησε νωρίτερα φέτος λόγω του καιρού.", ["plist", "strat"]),
    ("Give examples of KPIs for an export sales team.", ["sal", "strat"]),
    ("Ποια είναι η διαφορά μεταξύ σύμβασης έργου και εξαρτημένης εργασίας;", ["hr", "sal"]),
    ("Explain what a force majeure clause is.", ["nord", "board"]),
    ("Φτιάξε πρότυπο μηνιαίου report πωλήσεων χωρίς πραγματικά δεδομένα.", ["strat", "plist"]),
    ("Does the EU require allergen labels on olive oil bottles?", ["plist", "hr"]),
    ("How can I reduce food waste in a small production plant?", ["board", "hr"]),
    ("Calculate how many bottles are in 12 pallets of 48 cases with 6 bottles each.", ["plist", "nord"]),
    ("Convert 5,000 litres to kilograms using a density of 0.916.", ["price", "plist"]),
    ("Η συνάντηση είναι στις 14:30 στο δωμάτιο 12, επιβεβαίωσε με τη reception.", ["hr", "board"]),
]

GENERIC += [
    ("Make this sound friendlier: We cannot approve the request this week.", ["hr", "nord"]),
    ("Διόρθωσε τα ορθογραφικά: Ευχαριστώ πολύ για την βοήθια σας και ελπίζω να τα πούμε σύντομα.", ["hr", "plist"]),
    ("Rewrite in a formal tone: hey, just checking if you got my last message?", ["nord", "plist"]),
    ("Συντόμευσε αυτή την πρόταση: Θα ήθελα να σας ενημερώσω ότι η συνάντηση που είχαμε προγραμματίσει έχει μετατεθεί.", ["board", "hr"]),
    ("Translate to English: Η εβδομάδα ξεκίνησε καλά και η ομάδα είναι χαρούμενη.", ["strat", "hr"]),
    ("Summarise in one line: The new coffee machine in the kitchen is working again after the repair.", ["hr", "board"]),
    ("Give me three subject lines for a thank you email after a trade fair.", ["plist", "strat"]),
    ("Βάλε σε λίστα: αγορά χαρτιού, μελάνι εκτυπωτή, νέα πρίζα για το γραφείο.", ["board", "hr"]),
    ("Fix the grammar: The team have finish the report yesterday and sends it today.", ["strat", "nord"]),
    ("Rephrase politely: You are late again and this is unacceptable.", ["hr", "sal"]),
    ("Check whether this IBAN looks well formed: GR00 0000 0000 0000 0000 0000 000", ["nord", "plist"]),
    ("Το τιμολόγιο 2028/001234 είναι 3.450,00 ευρώ με ΦΠΑ· γράψε ένα σύντομο σημείωμα για το λογιστήριο.", ["plist", "nord"]),
    ("Add 24% VAT to a net amount of 1.250 euros and show the calculation.", ["price", "plist"]),
    ("Η αποστολή 778-4421 φεύγει Τρίτη, φτιάξε ένα μήνυμα προς τον μεταφορέα.", ["nord", "plist"]),
    ("Convert 250 grams of olives to ounces and give me the number.", ["plist", "strat"]),
    ("What is 12.5 percent of 480?", ["price", "sal"]),
    ("Ο κωδικός προϊόντος AB-5521 δεν βρίσκεται στο σύστημα, πώς το ελέγχω;", ["plist", "price"]),
    ("Tracking code TX 90 4412 shows the parcel is in Athens, reply to the customer.", ["nord", "plist"]),
    ("According to the International Olive Council, Spain is the world's largest olive oil producer. Summarise this for a slide.", ["strat", "plist"]),
    ("Η ελληνική κατανάλωση ελαιολάδου ανά κάτοικο είναι από τις υψηλότερες στον κόσμο· γράψε μια φράση για το ενημερωτικό δελτίο.", ["plist", "strat"]),
    ("The EU minimum VAT rate is set by directive, explain it in two sentences.", ["price", "plist"]),
    ("Σύμφωνα με τη Eurostat η ανεργία στην ευρωζώνη υποχώρησε το τελευταίο έτος, κάνε μια περίληψη.", ["hr", "sal"]),
    ("Public data say the harvest in the Mediterranean usually runs from October to January, add that to the leaflet.", ["plist", "board"]),
    ("Το ελαιόλαδο περιέχει κυρίως μονοακόρεστα λιπαρά οξέα, εξήγησέ το απλά.", ["plist", "hr"]),
    ("Per the European Commission, labels must show the country of origin for virgin olive oil. Write a reminder for the packaging team.", ["plist", "board"]),
    ("Write a two line farewell message for a colleague who is retiring next month.", ["hr", "sal"]),
    ("Πρότεινε τρεις τίτλους για ένα άρθρο σχετικά με τα οφέλη της μεσογειακής διατροφής.", ["plist", "strat"]),
    ("Make this paragraph shorter without losing the main point: The workshop covered several topics including planning, tools and teamwork.", ["strat", "hr"]),
    ("Μετάφρασε στα ελληνικά: Thank you for your patience while we fix the website.", ["plist", "strat"]),
    ("Turn these notes into a short email: meeting moved, bring laptops, lunch provided.", ["hr", "board"]),
    ("Which format is better for a customer survey, five stars or a number from one to ten?", ["strat", "plist"]),
]

FRAMES_EL = ["", "", "Βελτίωσε τη διατύπωση: {t}", "Μπορείς να το συνοψίσεις; {t}",
             "Γράψε το σε email: {t}", "Έλεγξε αν αυτό είναι σωστό: {t}", "Χρειάζομαι βοήθεια με το εξής: {t}"]
FRAMES_EN = ["", "", "Can you tidy this up? {t}", "Please summarise: {t}",
             "Put this in an email: {t}", "Is this right? {t}", "I need help with this: {t}"]

# ---------------------------------------------------------------- entities
FIRST = [("Ελένη", "Eleni", "f"), ("Γιώργος", "Giorgos", "m"), ("Κατερίνα", "Katerina", "f"),
         ("Πάνος", "Panos", "m"), ("Άργυρω", "Argyro", "f"), ("Λευτέρης", "Lefteris", "m"),
         ("Ξένια", "Xenia", "f"), ("Ορέστης", "Orestis", "m"), ("Δέσποινα", "Despina", "f"),
         ("Βαγγέλης", "Vangelis", "m"), ("Μαριλένα", "Marilena", "f"), ("Θάνος", "Thanos", "m"),
         ("Ιωάννα", "Ioanna", "f"), ("Helen", "Helen", "f"), ("Tom", "Tom", "m"),
         ("Priya", "Priya", "f"), ("Oliver", "Oliver", "m")]
# (Greek form, Latin form): endings that need no case change in Greek sentences
SURNAMES = [("Παπαδάκη", "Papadaki"), ("Δήμου", "Dimou"), ("Κάλλη", "Kalli"), ("Σιδέρη", "Sideri"),
            ("Μαυρογένη", "Mavrogeni"), ("Ζαφείρη", "Zafeiri"), ("Φωτιάδη", "Fotiadi"), ("Σπύρη", "Spyri"),
            ("Ρούσση", "Roussi"), ("Τζίμα", "Tzima"), ("Νικολάκη", "Nikolaki"), ("Καναρά", "Kanara"),
            ("Ντάλλα", "Dalla"), ("Γκουρά", "Gkoura"), ("Στάμου", "Stamou"), ("Χαλκιά", "Chalkia"),
            ("Βρέλλη", "Vrelli"), ("Κανάκης", "Kanakis"), ("Marsh", "Marsh"), ("Hadley", "Hadley"),
            ("Raman", "Raman"), ("Finch", "Finch"), ("Whitcombe", "Whitcombe"), ("Dunmore", "Dunmore")]

EL_PERSON = [
    "{A} {n} θα παρουσιάσει τα αποτελέσματα στη συνεδρίαση της Δευτέρας.",
    "Στο email του HR αναφέρεται ότι {a} {n} έχει πάρει προειδοποίηση για τις απουσίες.",
    "Σύμφωνα με τον φάκελο, {a} {n} εξετάζεται για απόλυση.",
    "Ρώτησε το λογιστήριο αν {a} {n} έχει εγκριθεί για το μπόνους συγκομιδής.",
    "Γράψε σημείωση: {A} {n} ζήτησε μετάθεση στην Τρίπολη.",
    "Μην πεις σε κανέναν ότι {a} {n} παίρνει υψηλότερο μισθό από τους υπόλοιπους.",
    "Η αξιολόγηση που έκανε {a} {n} για την ομάδα παραγωγής ήταν αρνητική.",
]
EN_PERSON = [
    "Please remind {first} {n} to send the signed contract by Friday.",
    "{first} {n} told me the harvest bonus is not in the contract.",
    "Can you draft a warning letter for {first} {n} about missed shifts?",
    "Schedule a call with {first} {n} about the Nordmarkt renewal.",
    "Who approved the discount, {first} {n} or the sales manager?",
    "I heard {first} {n} is being considered for dismissal, don't tell anyone.",
    "Write a short reference letter for {first} {n}, who worked on our bottling line.",
]
SURNAME_ONLY = [  # surname alone, no first name (the hard case the pipeline's Greek model misses)
    "Συνάντηση με {n}: η συζήτηση αφορά την αξιολόγηση και τον μισθό.",
    "Ρώτα την {n} για τα στοιχεία του φακέλου πριν την Παρασκευή.",
    "Forward the salary question to {n} in finance.",
    "{n} will be promoted in March and the pay will go up.",
    "Tell {n} that the warning stays in the file.",
    "Ask {n} whether the Evripos order can ship on Monday.",
]
# look-alike words: (span, [sentences]); none is a person
LOOKALIKE = [
    ("Δήμου", ["Η απόφαση του Δήμου Καλαμάτας για τα τέλη καθαριότητας δημοσιεύθηκε χθες.",
               "Ο προϋπολογισμός του Δήμου Σπάρτης ψηφίστηκε από το δημοτικό συμβούλιο.",
               "Χρειαζόμαστε άδεια του Δήμου για το περίπτερο στην αγορά."]),
    ("Καλή", ["Σας ευχόμαστε Καλή Σοδειά και καλή συγκομιδή σε όλους.",
              "Της είπα Καλή Επιτυχία πριν την παρουσίαση."]),
    ("Ελιά", ["Η Ελιά Καλαμών είναι ποικιλία με ονομασία προέλευσης.",
              "Φέτος η Ελιά έδωσε λιγότερο καρπό λόγω ξηρασίας."]),
    ("Ταΰγετο", ["Η σοδειά φέτος στον Ταΰγετο ήταν μικρότερη λόγω ξηρασίας.",
                 "Τα ελαιόδεντρα στον Ταΰγετο ανθίζουν αργότερα από της πεδιάδας."]),
    ("Μεσσηνία", ["Στη Μεσσηνία η συγκομιδή ξεκινά συνήθως τον Νοέμβριο.",
                  "Πολλά ελαιουργεία της Μεσσηνίας δουλεύουν όλο τον χειμώνα."]),
    ("Τρίπολη", ["Το τρένο για την Τρίπολη αναχωρεί το πρωί, φτιάξε μου πρόγραμμα ταξιδιού.",
                 "Πόσα χιλιόμετρα απέχει η Τρίπολη από την Καλαμάτα;"]),
    ("Κορωνέικη", ["Η Κορωνέικη είναι η πιο διαδεδομένη ποικιλία ελιάς στην Πελοπόννησο.",
                   "Πώς διαφέρει η Κορωνέικη από τη Μανάκι στη γεύση;"]),
    ("Σπάρτη", ["Η Σπάρτη είχε πρωτεύουσα της Λακωνίας και πολλά αρχαία μνημεία.",
                "Θέλω ιδέες για μια εκδρομή στη Σπάρτη το Σαββατοκύριακο."]),
    ("Mark", ["Please mark the pallets as fragile before loading.", "Mark the shipment as delayed in the tracking sheet."]),
    ("Will", ["Will the shipment arrive before Friday if we pay for express?", "Explain what a will is and when a company needs a lawyer."]),
    ("Grace", ["The contract template has a ten day grace period for late payments.", "Explain what a grace period means in a loan."]),
    ("Bill", ["Send the bill to accounting once the order is closed.", "How do I split a bill between two cost centres?"]),
    ("Rose", ["Rose petals can be used in the gift box packaging for the spring line.", "The Rose variety of grape is not used for olive oil."]),
    ("Chase", ["Chase the supplier for the missing label proofs by Thursday.", "How do I chase a late payment politely?"]),
    ("Frank", ["Let's have a frank discussion about the delays with the carrier.", "I need frank feedback on this packaging design."]),
    ("Pat", ["Pat the bottles dry before applying the labels.", "Show the steps to pat dry and wrap each bottle."]),
    ("Sage", ["Sage accounting software exports invoices as csv files.", "Add sage and thyme to the herb oil recipe."]),
    ("Amber", ["Amber glass bottles protect the oil from light better than clear glass.", "Compare amber and green glass for oil bottles."]),
    ("Grant", ["The EU grant covers part of the machinery cost, help me write the report.", "How do I apply for a regional grant for food producers?"]),
    ("Price", ["Price lists are updated every spring, remind me how to format one.", "Explain what a price elasticity is."]),
    ("Taylor", ["Taylor the offer to each retailer's size and region.", "How can we taylor our newsletter to smaller shops?"]),
    ("Hope", ["We hope the new line is ready before the harvest peak.", "Write a hopeful closing line for the newsletter."]),
]
PUBLIC_FIGURES = [
    ("Αριστοτέλης", "Ο Αριστοτέλης έγραψε για τη φύση και τις αρετές των τροφίμων."),
    ("Ιπποκράτης", "Ο Ιπποκράτης έλεγε να είναι η τροφή σου το φάρμακό σου, βάλε το σε ομιλία."),
    ("Περικλής", "Ο Περικλής ηγήθηκε της Αθήνας στη χρυσή εποχή της και θέλω μια περίληψη."),
    ("Σωκράτης", "Ο Σωκράτης δίδασκε με ερωτήσεις, πώς μπορώ να το εφαρμόσω στην εκπαίδευση;"),
    ("Aristotle", "Aristotle wrote about ethics, summarise his main idea in two sentences."),
    ("Archimedes", "Archimedes discovered the principle of buoyancy, explain it simply."),
    ("Hippocrates", "Hippocrates is often called the father of medicine, write a short intro."),
    ("Pericles", "Pericles gave a famous funeral oration, give me the context."),
    ("Homer", "Homer wrote about olive trees in the Odyssey, find a nice quote for the label."),
    ("Napoleon", "Napoleon introduced the civil code in France, summarise it for a presentation."),
]
LOOKALIKE += [
    ("Baker", ["Baker's yeast is sold in small packets by the till, add it to the supplies list."]),
    ("Porter", ["Porter beer pairs well with dark chocolate, suggest a menu for the tasting."]),
    ("Archer", ["Archer fish can spit water at insects, find a fun fact for the newsletter."]),
    ("Fisher", ["Fisher boats leave the harbour at dawn, describe the scene for the label story."]),
    ("Wood", ["Wood from old olive trees is used for kitchen boards, write a product blurb."]),
    ("Hill", ["The Hill behind the mill is covered with young trees, describe it for the visitor leaflet."]),
    ("Field", ["Field notes from the harvest are due on Friday, remind the team."]),
    ("Gold", ["Gold medals at the oil competition go on the website, update the awards page."]),
    ("Μάρτιο", ["Η σύσκεψη μεταφέρεται τον Μάρτιο λόγω των εορτών.", "Τον Μάρτιο κλαδεύουμε τα ελαιόδεντρα και προγραμματίζουμε τις εργασίες."]),
    ("Πάσχα", ["Το Πάσχα το εργοστάσιο κλείνει για τρεις ημέρες, ενημέρωσε τους πελάτες."]),
    ("Σάββατο", ["Το Σάββατο η γραμμή παραγωγής δουλεύει κανονικά με μειωμένο προσωπικό."]),
    ("Καλαμάτα", ["Από την Καλαμάτα στο λιμάνι της Πάτρας η διαδρομή κρατά περίπου τρεις ώρες."]),
    ("Ιόνιο", ["Το Ιόνιο έχει ήπιο κλίμα που ευνοεί την ελιά, γράψε μια παράγραφο."]),
    ("Olive", ["Olive branches are a symbol of peace, use that in the label story."]),
    ("Brown", ["Brown paper wrapping looks natural for the gift boxes."]),
    ("Bay", ["Bay leaves infuse nicely in flavoured oil, share a recipe."]),
    ("Mason", ["Mason jars work well for small batches of preserved olives."]),
    ("Page", ["Turn to Page twelve of the catalogue to check the bottle sizes."]),
    ("Rich", ["Rich flavours develop in late harvest oil, rewrite this for the label."]),
    ("Lane", ["The loading Lane is blocked by a pallet, please move it."]),
    ("Max", ["Set Max temperature for the tank to the safe limit in the checklist."]),
    ("Joy", ["Add some Joy to the holiday gift box wording."]),
    ("Art", ["The label Art needs approval before the printer starts."]),
]
PUBLIC_FIGURES += [
    ("Θουκυδίδης", "Ο Θουκυδίδης έγραψε την ιστορία του Πελοποννησιακού πολέμου, κάνε μια περίληψη."),
    ("Ηρόδοτος", "Ο Ηρόδοτος θεωρείται ο πατέρας της ιστορίας, γράψε ένα σύντομο κείμενο."),
    ("Πλάτων", "Ο Πλάτων ίδρυσε την Ακαδημία, εξήγησε το σε μαθητές γυμνασίου."),
    ("Newton", "Newton described gravity, explain the idea for a children's workshop."),
    ("Einstein", "Einstein published the theory of relativity in the early twentieth century, summarise."),
    ("Leonardo da Vinci", "Leonardo da Vinci painted the Last Supper, write two lines for a gift card."),
    ("Cleopatra", "Cleopatra ruled Egypt and was famous for her use of oils, give me a fun fact."),
    ("Ιπποκράτη", "Ο γιατρός που ακολουθεί τον όρκο του Ιπποκράτη δεσμεύεται να μην βλάψει κανέναν."),
]

SURNAMES += [("Σταμάτη", "Stamati"), ("Ξένου", "Xenou"), ("Λάμπρου", "Lambrou"), ("Γιαννακού", "Giannakou"),
             ("Τσίρου", "Tsirou"), ("Βαρελά", "Varela"), ("Σαββίδη", "Savvidi"), ("Τσιμάρα", "Tsimara"),
             ("Μπεκιάρη", "Bekiari"), ("Νικολαΐδη", "Nikolaidi"), ("Καλογήρου", "Kalogirou"), ("Ιωαννίδη", "Ioannidi")]
SURNAME_ONLY += [
    "Πες στην {n} να περάσει από το HR αύριο το πρωί.", "Ο μισθός της {n} αναθεωρείται τον Ιανουάριο, μην το πεις σε κανέναν.",
    "Η αξιολόγηση της {n} ήταν θετική, γράψε μια σύντομη σημείωση.",
    "Don't forward this to {n}, it is about the pay review.", "{n} is on sick leave until Friday, move the meeting.",
    "Ask {n} for the signed contract before we ship.", "I spoke with {n} about the transfer to the Kalamata mill.",
]
EN_PERSON += [
    "Could you check the holiday balance of {first} {n} before payroll closes?",
    "{first} {n} will lead the new bottling line project from March.",
    "Please send the draft contract to {first} {n} and keep it confidential.",
]
LOOKALIKE += [
    ("Summer", ["Summer sales usually peak in July, add a note to the forecast template."]),
    ("Dawn", ["Dawn deliveries save time, write a note to the drivers about the early schedule."]),
    ("Hunter", ["The Hunter green label was approved by the printer, update the proof."]),
    ("Faith", ["Have some faith in the process and keep the team calm, rewrite this for a newsletter."]),
    ("Lily", ["Lily pads float on the pond behind the mill, write a short caption for the photo."]),
    ("Ivy", ["Ivy covers the old stone wall of the mill, describe it in one sentence."]),
    ("Crystal", ["Crystal clear bottles show the colour of the oil, suggest a tagline."]),
    ("Pearl", ["Pearl onions are on the supplier list for the pickles line."]),
    ("Ruby", ["Ruby grapefruit slices go well with oil and herbs, write a menu note."]),
    ("Violet", ["Violet labels are for the lavender range, check the artwork."]),
    ("Heather", ["Heather honey is sold at the visitor shop, add it to the price board."]),
    ("Κρόνος", ["Ο Κρόνος είναι ο δεύτερος σε μέγεθος πλανήτης του ηλιακού συστήματος, εξήγησέ το σε παιδιά."]),
]
PUBLIC_FIGURES += [
    ("Σεφέρης", "Ο Σεφέρης τιμήθηκε με Νόμπελ λογοτεχνίας το 1963, γράψε μια σύντομη εισαγωγή."),
    ("Παπαδιαμάντης", "Ο Παπαδιαμάντης έγραψε διηγήματα για τη Σκιάθο, κάνε μια περίληψη για μαθητές."),
    ("Θεοδωράκης", "Ο Μίκης Θεοδωράκης συνέθεσε τη μουσική του Ζορμπά, βρες μια ωραία φράση για την πρόσκληση."),
    ("Charles Darwin", "Charles Darwin published On the Origin of Species in 1859, explain the idea in two lines."),
    ("Galileo", "Galileo observed the moons of Jupiter with a telescope, write a short caption for the poster."),
    ("Shakespeare", "Shakespeare wrote Hamlet around the year 1600, give me a quote for the card."),
    ("Mozart", "Mozart began composing as a child, write a fun fact for the newsletter."),
    ("Alexander Fleming", "Alexander Fleming discovered penicillin in 1928, summarise it for the school visit."),
    ("Dante", "Dante wrote the Divine Comedy, write one sentence for the library display."),
    ("Mother Teresa", "Mother Teresa received the Nobel Peace Prize, add a line to the charity page."),
]
CLIENTS2 = [("Kronos Retail", "Kronos"), ("Meltemi Cafés", "Meltemi"), ("Pelagos Catering", "Pelagos"), ("Brisa Markets", "Brisa"),
            ("Tavira Gourmet", "Tavira"), ("Aldenmoor Fine Foods", "Aldenmoor"), ("Lumenor Hotels", "Lumenor"),
            ("Varnavas Trading", "Varnavas"), ("Ostria Delicatessen", "Ostria"), ("Solenne Épicerie", "Solenne"),
            ("Κρόνος Retail", "Κρόνος"), ("Μελτέμι Καφέδες", "Μελτέμι"), ("Πέλαγος Catering", "Πέλαγος")]
CLIENT2_EN = [
    "Please prepare the price list for {c} before Thursday's call.",
    "{c} complained that the last pallet arrived damaged, draft an apology.",
    "Our contract with {c} ends in June, list the points we should renegotiate.",
    "Send the invoice to {c} and copy the export team.",
    "What discount did we agree with {c} last year?",
    "{c} wants to add organic oil to its next order, check stock.",
    "Write a short note for the sales meeting about the order from {c}.",
    "Is {c} still on the approved list for the Gulf shipment?",
]
CLIENT2_EL = [
    "Ετοίμασε τον τιμοκατάλογο για την {c} πριν την κλήση της Πέμπτης.",
    "Η {c} παραπονέθηκε ότι η τελευταία παλέτα έφτασε χαλασμένη, γράψε μια συγγνώμη.",
    "Το συμβόλαιο με την {c} λήγει τον Ιούνιο, γράψε τι πρέπει να ξαναδιαπραγματευτούμε.",
    "Στείλε το τιμολόγιο στην {c} και βάλε σε κοπία την ομάδα εξαγωγών.",
    "Ποια έκπτωση συμφωνήσαμε με την {c} πέρυσι;",
    "Η {c} θέλει να προσθέσει βιολογικό λάδι στην επόμενη παραγγελία, έλεγξε το απόθεμα.",
]
CLIENT2_NO = [
    ("Kronos", "In Greek mythology Kronos was the father of Zeus, write two lines for the school quiz."),
    ("Meltemi", "The Meltemi wind blows strongly in August, write a weather note for the guests."),
    ("πέλαγος", "Το Αιγαίο πέλαγος ήταν ήρεμο σήμερα, φτιάξε ένα σύντομο ποστ για τα μέσα κοινωνικής δικτύωσης."),
    ("brisa", "A light brisa from the sea cools the terrace in the evening, translate this phrase."),
    ("μελτέμι", "Το μελτέμι φέτος ήρθε νωρίς και τα καΐκια έμειναν στο λιμάνι, κάνε το πιο λογοτεχνικό."),
    ("Tavira", "Tavira is a small town in the Algarve, suggest a weekend trip plan."),
    ("Solenne", "A solenne ceremony opens the festival every year, polish this sentence."),
    ("όστρια", "Η όστρια φυσάει από τον νότο και φέρνει υγρασία, εξήγησέ το σε μαθητές."),
]
CLIENT_SPANS = ["Nordmarkt Feinkost", "Nordmarkt", "Evripos Supermarkets", "Evripos", "Baltic Delikatessen", "Baltic"]
CLIENT_YES_EN = [
    "{c} wants to renegotiate the supply contract before the harvest.",
    "Send the revised price offer to {c} by tomorrow.",
    "Prepare talking points for the call with {c} about the late delivery.",
]
CLIENT_YES_EL = [
    "Η {c} ζήτησε νέα τιμή για την επόμενη παραγγελία.",
    "Ετοίμασε την προσφορά για την {c} και στείλ' την σήμερα.",
]
CLIENT_NO = [
    ("Baltic", "Ice on the Baltic Sea closes some shipping routes in January."),
    ("Baltic", "Baltic birch plywood makes good packing crates for the pallets."),
    ("Evripos", "Ferries cross the Evripos channel near Chalkida every few minutes."),
    ("Evripos", "The strong tidal currents of the Evripos strait are a famous natural curiosity."),
    ("Nordmarkt", "Translate the German word Nordmarkt as a place name on the map legend."),
]
CLIENT_NO += [
    ("Baltic", "Baltic amber is sold at the fair next to the olive oil stand."),
    ("Evripos", "Evripos is the Greek name of the strait, add it to the map caption."),
]
SALARY_YES = [
    ("el", "Ο ετήσιος μισθός της βαθμίδας είναι {x}.", ["36.000 ευρώ", "28 χιλιάδες ευρώ", "52.500 ευρώ", "41.000€"]),
    ("el", "Ο υπεύθυνος παραγωγής αμείβεται με {x} τον χρόνο.", ["33.000 ευρώ", "45 χιλιάδες", "39.500€"]),
    ("el", "Πρότεινε στον νέο συνεργάτη μισθό {x} συν το επίδομα συγκομιδής.", ["30.000 ευρώ", "27.500€", "34 χιλιάδες ευρώ"]),
    ("en", "The export director's base salary is {x}.", ["€68,000", "68k euros", "70,000 euros a year"]),
    ("en", "Offer the new hire {x} a year plus the harvest allowance.", ["€31,000", "29k", "35,500 euros"]),
    ("en", "She earns {x} gross per year, please keep that private.", ["€44,000", "47k", "42,500 euros"]),
    ("en", "Monthly pay for a first grade production worker is {x}.", ["1,850 euros", "€1,900", "2,100 euros"]),
]
AMOUNT_NO = [
    ("el", "Η δεξαμενή χωράει {x} ελαιολάδου και δεν πρέπει να υπερχειλίσει.", ["36.000 λίτρα", "40.000 λίτρα", "28.500 λίτρα"]),
    ("el", "Φόρτωσε στο φορτηγό {x} και στείλε την αποδεικτική φωτογραφία.", ["12 παλέτες", "40 παλέτες", "18 παλέτες"]),
    ("el", "Το πρότυπο {x} αφορά την ασφάλεια των τροφίμων και τα προσωπικά δεδομένα δεν σχετίζονται.", ["ISO 22000", "ISO 9001", "HACCP 2005"]),
    ("el", "Σύμφωνα με τη στατιστική υπηρεσία, ο κατώτατος μισθός στην Ελλάδα είναι δημόσια πληροφορία: {x}.", ["880 ευρώ τον μήνα", "830 ευρώ τον μήνα"]),
    ("el", "Ο ΦΠΑ στα τρόφιμα είναι {x}, βάλ' το στο υπολογιστικό φύλλο.", ["13%", "24%"]),
    ("el", "Η παραγγελία με αριθμό {x} εκκρεμεί στην αποθήκη.", ["4521", "7783", "9102"]),
    ("en", "The tank holds {x} of oil and must not overflow during bottling.", ["36,000 litres", "28,500 litres", "40,000 litres"]),
    ("en", "Load {x} onto the truck and send the proof photo.", ["12 pallets", "40 pallets", "18 pallets"]),
    ("en", "The certificate {x} covers food safety and has nothing to do with staff.", ["ISO 22000", "ISO 9001", "HACCP"]),
    ("en", "According to Eurostat the public average pay in food manufacturing is {x}, add it to the slide.", ["31,000 euros", "28,400 euros"]),
    ("en", "The statutory minimum wage in Greece is public: {x}.", ["880 euros a month", "830 euros a month"]),
    ("en", "Our year of founding was {x}, add it to the about page.", ["1987", "1994"]),
    ("en", "Shipment {x} left the port on Tuesday, please update the tracking sheet.", ["no. 4521", "no. 7783"]),
]
PHONE_YES = [("el", "Κάλεσε την {n} στο {p} για να επιβεβαιώσει την άδεια του Πάνου."),
             ("en", "Call {n} on {p} to confirm the shift change."),
             ("en", "Text {n} at {p} that the HR meeting moved to Monday.")]
PHONE_NO = [("el", "Η αποστολή με κωδικό παρακολούθησης {p} βρίσκεται στο Αμβούργο."),
            ("en", "Tracking number {p} shows the pallet is in Hamburg."),
            ("en", "Invoice reference {p} is waiting for approval.")]

REASONS = {
    "doc_yes": {
        "paraphrase": ["Closely rewords the {d}, including its key figures.",
                       "Paraphrases the {d}; the same facts and figures appear.",
                       "Restates confidential content of the {d} in new words."],
        "cross": ["Translates the {d} content into the other language.",
                  "Same facts as the {d}, written in another language."],
        "summary": ["Summarises the {d} and repeats its key numbers.",
                    "Short summary of the {d} that keeps the figures."],
        "copy": ["Copies part of the {d} text.", "Reuses a passage of the {d} nearly word for word."],
    },
    "doc_no": ["Same topic as the {d}; asks nothing confidential.",
               "Question about the topic only; no {d} content revealed.",
               "General knowledge request, not the {d} content."],
    "generic_no": ["Generic question; nothing from the {d} is revealed.",
                   "Public or general topic, no company data involved.",
                   "General request unrelated to the {d} content."],
    "public_no": ["The matched document is public; nothing confidential.",
                  "Public newsletter content, free to share."],
    "PERSON_yes": ["Real person name of a colleague in a work context.",
                   "Genuine surname referring to a company employee.",
                   "Actual staff member named together with personal details."],
    "PERSON_no": ["Common word or place name, not a person.",
                  "Ordinary noun or verb that only resembles a name.",
                  "Municipality or place, not a person name."],
    "PUBLIC_no": ["Well known historical figure, not a company person.",
                  "Public figure from history, no private person involved."],
    "CLIENT_yes": ["Names a company customer in a business context.",
                   "Refers to a real client by name."],
    "CLIENT_no": ["Geographic term matching a client name by chance.",
                  "Place or material word, not the client company."],
    "AMOUNT_yes": ["Compensation figure for an employee or role.", "Salary amount tied to a job or person."],
    "AMOUNT_no": ["Quantity, date or reference, not a salary.", "Public statistic or identifier, not company pay.",
                  "Measure of goods or a certificate, not compensation."],
    "PHONE_yes": ["Genuine phone number of a named colleague."],
    "PHONE_no": ["Tracking or invoice reference, not a phone number."],
}


# ---------------------------------------------------------------- helpers
def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join("σ" if c == "ς" else c for c in s if not unicodedata.combining(c))


def toks(s: str) -> list[str]:
    return re.findall(r"\w+", fold(s))


def shingles(s: str, n: int) -> set[tuple[str, ...]]:
    t = toks(s)
    return {tuple(t[i : i + n]) for i in range(max(0, len(t) - n + 1))}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def load_doc(key: str) -> tuple[str, str, str]:
    raw = (TRAIN_ORG / DOCS[key][0]).read_text(encoding="utf-8")
    if raw.startswith("---"):
        _, front, body = raw.split("---", 2)
        title = re.search(r'title:\s*"?(.*?)"?\s*$', front, re.M).group(1)
        sens = re.search(r"sensitivity:\s*(\w+)", front).group(1)
        return title, sens, body.strip()
    first = raw.split("\n", 1)[0].strip('" ')
    return "Pricing engine (Python)", "restricted", raw.strip()


def best_overlap(anchor: str, options: list[str]) -> int:
    a = set(toks(anchor))
    scores = [len(a & set(toks(o))) for o in options]
    return scores.index(max(scores))


def sentences(body: str) -> list[str]:
    parts = []
    for line in body.split("\n"):
        parts.extend(p.strip() for p in re.split(r"(?<=[.;·])\s+", line) if p.strip())
    return parts


def frame_for(rng: random.Random, text: str) -> str:
    frames = FRAMES_EL if language(text) == "el" else FRAMES_EN
    f = rng.choice(frames)
    return f.format(t=text) if f else text


def make(prompt: str, cand: dict, verdict: str, reason: str, meta: dict) -> dict:
    assert reason_ok(reason), reason
    return {"prompt": prompt, "cand": cand, "verdict": verdict, "reason": reason, "meta": meta}


# ---------------------------------------------------------------- generation
def doc_examples(rng: random.Random) -> list[dict]:
    docs = {k: load_doc(k) for k in DOCS}
    chunks = {k: chunk_text(docs[k][2]) for k in DOCS}
    out: list[dict] = []
    by_doc: dict[str, list[int]] = {}
    fact_chunk: list[int] = []
    for doc, anchor, *_ in FACTS:
        i = best_overlap(anchor, chunks[doc])
        a = set(toks(anchor))
        if len(a & set(toks(chunks[doc][i]))) < min(3, len(a)):
            raise SystemExit(f"anchor not found in {doc}: {anchor!r}")
        fact_chunk.append(i)
        by_doc.setdefault(doc, []).append(i)

    def cand(doc: str, idx: int, prompt: str, kind: str, positive: bool) -> dict:
        title, sens, _ = docs[doc]
        chunk = chunks[doc][idx]
        pl, cl = language(prompt), language(chunk)
        same = pl == cl
        if kind == "copy":
            score = rng.uniform(0.5, 0.88)
        elif positive:
            score = rng.gauss(0.91 if same else 0.895, 0.025)
        else:
            score = rng.gauss(0.89 if same else 0.875, 0.02)
        floor = 0.88 if same else 0.86
        if kind != "copy":
            score = min(0.97, max(floor, score))
        return doc_candidate(title, sens, kind, score, pl, cl, chunk)

    for k, ((doc, anchor, same_p, cross_p, summ, safe), ci) in enumerate(zip(FACTS, fact_chunk)):
        safe = list(safe) + EXTRA_SAFE[k]
        short = DOCS[doc][1]
        body = docs[doc][2]
        sents = sentences(body)
        orig = sents[best_overlap(anchor, sents)]
        for text in same_p:
            p = frame_for(rng, text)
            out.append(make(p, cand(doc, ci, p, "paraphrase", True), "YES",
                            rng.choice(REASONS["doc_yes"]["paraphrase"]).format(d=short),
                            {"type": "doc_chunk", "sub": "paraphrase_same", "doc": doc}))
        for text in cross_p:
            p = frame_for(rng, text)
            out.append(make(p, cand(doc, ci, p, "paraphrase", True), "YES",
                            rng.choice(REASONS["doc_yes"]["cross"]).format(d=short),
                            {"type": "doc_chunk", "sub": "paraphrase_cross", "doc": doc}))
        out.append(make(summ, cand(doc, ci, summ, "paraphrase", True), "YES",
                        rng.choice(REASONS["doc_yes"]["summary"]).format(d=short),
                        {"type": "doc_chunk", "sub": "summary_numbers", "doc": doc}))
        w = orig.split()
        for _ in range(3):  # different slices of the same sentence
            if len(w) >= 8:
                n = max(6, int(len(w) * rng.uniform(0.5, 0.8)))
                s = rng.randint(0, len(w) - n)
                part = " ".join(w[s : s + n])
            else:
                part = orig
            p = frame_for(rng, part)
            out.append(make(p, cand(doc, ci, p, "copy", True), "YES",
                            rng.choice(REASONS["doc_yes"]["copy"]).format(d=short),
                            {"type": "doc_chunk", "sub": "partial_copy", "doc": doc}))
        for _ in range(2):  # short fragments (6 to 9 words): a piece of a document pasted on its own
            if len(w) < 10:
                break
            n = rng.randint(6, 9)
            s = rng.randint(0, len(w) - n)
            frag = " ".join(w[s : s + n])
            p = frame_for(rng, frag) if rng.random() < 0.5 else frag
            out.append(make(p, cand(doc, ci, p, "copy", True), "YES",
                            rng.choice(REASONS["doc_yes"]["copy"]).format(d=short),
                            {"type": "doc_chunk", "sub": "fragment_copy", "doc": doc}))
        others = [j for j in range(len(chunks[doc])) if j != ci]
        for text in safe:
            for j in [ci] + rng.sample(others, min(2, len(others))):
                out.append(make(text, cand(doc, j, text, "paraphrase", False), "NO",
                                rng.choice(REASONS["doc_no"]).format(d=short),
                                {"type": "doc_chunk", "sub": "same_topic_safe", "doc": doc, "hard": True}))
    for pkey, pfacts in (("pub", PUBLIC_FACTS), ("pub2", PUBLIC_FACTS2)):
        pub_sents = sentences(docs[pkey][2])
        for anchor, texts in pfacts:
            ci = best_overlap(anchor, chunks[pkey])
            orig = pub_sents[best_overlap(anchor, pub_sents)]
            w = orig.split()
            parts = list(texts)
            for _ in range(3):  # partial copies of a public text are fine too
                n = max(6, int(len(w) * rng.uniform(0.5, 0.8)))
                s = rng.randint(0, len(w) - n)
                parts.append(" ".join(w[s : s + n]))
            for k, text in enumerate(parts):
                p = frame_for(rng, text)
                kind = "copy" if k >= len(texts) else "paraphrase"
                out.append(make(p, cand(pkey, ci, p, kind, False), "NO", rng.choice(REASONS["public_no"]),
                                {"type": "doc_chunk", "sub": "public_doc", "doc": pkey, "hard": True}))
    for doc, anchor, pos_q, neg_q in DOC_EXTRA:
        ci = best_overlap(anchor, chunks[doc])
        short = DOCS[doc][1]
        out.append(make(pos_q, cand(doc, ci, pos_q, "paraphrase", True), "YES",
                        rng.choice(REASONS["doc_yes"]["paraphrase"]).format(d=short),
                        {"type": "doc_chunk", "sub": "indirect_question", "doc": doc}))
        for j in [ci, rng.randrange(len(chunks[doc]))]:
            out.append(make(neg_q, cand(doc, j, neg_q, "paraphrase", False), "NO",
                            rng.choice(REASONS["doc_no"]).format(d=short),
                            {"type": "doc_chunk", "sub": "fictional_numbers", "doc": doc, "hard": True}))
    for text, topics in GENERIC:
        for doc in topics:
            idx = rng.randrange(len(chunks[doc]))
            out.append(make(text, cand(doc, idx, text, "paraphrase", False), "NO",
                            rng.choice(REASONS["generic_no"]).format(d=DOCS[doc][1]),
                            {"type": "doc_chunk", "sub": "generic_or_public", "doc": doc, "hard": True}))
    return out


def window(sentence: str, span: str, size: int = 7) -> str:
    w = sentence.split()
    key = fold(span.split()[0])
    pos = next((i for i, x in enumerate(w) if key in fold(x)), 0)
    lo, hi = max(0, pos - size), min(len(w), pos + size + len(span.split()))
    return " ".join(w[lo:hi])


def entity_examples(rng: random.Random) -> list[dict]:
    out: list[dict] = []

    def add(sentence: str, category: str, span: str, verdict: str, key: str, sub: str, hard: bool) -> None:
        found = re.search(re.escape(span), sentence, re.I)
        if found:
            span = found.group(0)  # the surface form as written, e.g. "mark" not "Mark"
        else:
            raise SystemExit(f"span {span!r} is not in its sentence: {sentence!r}")
        prompt = frame_for(rng, sentence) if rng.random() < 0.4 else sentence
        cand = entity_candidate(category, span, window(sentence, span))
        meta = {"type": "entity", "sub": sub, "category": category}
        if hard:
            meta["hard"] = True
        out.append(make(prompt, cand, verdict, rng.choice(REASONS[key]), meta))

    def person() -> tuple[str, str, str, str]:
        while True:  # never reuse a full name that already exists in the test data
            f = rng.choice(FIRST)
            s = rng.choice(SURNAMES)
            if not any(" ".join(toks(n)) in AVOID_FOLDED for n in (f"{f[0]} {s[0]}", f"{f[1]} {s[1]}")):
                return f[0], f[1], s[0], s[1]

    # real names: Greek script in Greek sentences, Latin script in English ones (a quarter swapped)
    for _ in range(40):
        fg, fl, sg, sl = person()
        art = "Ο" if next(x for x in FIRST if x[0] == fg)[2] == "m" else "Η"
        t = rng.choice(EL_PERSON)
        greek_name = rng.random() > 0.25
        first, sur = (fg, sg) if greek_name else (fl, sl)
        sent = t.format(A=art, a=art.lower(), n=f"{first} {sur}")
        add(sent, "PERSON", f"{first} {sur}", "YES", "PERSON_yes", "name_el_sentence", False)
    for _ in range(40):
        fg, fl, sg, sl = person()
        t = rng.choice(EN_PERSON)
        latin = rng.random() > 0.15
        first, sur = (fl, sl) if latin else (fg, sg)
        add(t.format(first=first, n=sur), "PERSON", f"{first} {sur}", "YES", "PERSON_yes", "name_en_sentence", False)
    for _ in range(60):  # surname alone, the Greek surnames without common endings
        sg, sl = rng.choice(SURNAMES)
        t = rng.choice(SURNAME_ONLY)
        name = sg if language(t) == "el" else sl
        add(t.format(n=name), "PERSON", name, "YES", "PERSON_yes", "surname_only", False)
    for span, sents in LOOKALIKE:
        for s in sents:
            add(s, "PERSON", span, "NO", "PERSON_no", "lookalike_word", True)
    for span, s in PUBLIC_FIGURES:
        add(s, "PERSON", span, "NO", "PUBLIC_no", "public_figure", True)

    for c in CLIENT_SPANS:
        for t in rng.sample(CLIENT_YES_EN, 2):
            add(t.format(c=c), "CLIENT", c, "YES", "CLIENT_yes", "client_name", False)
        add(rng.choice(CLIENT_YES_EL).format(c=c), "CLIENT", c, "YES", "CLIENT_yes", "client_name", False)
    for span, s in CLIENT_NO:
        add(s, "CLIENT", span, "NO", "CLIENT_no", "client_lookalike", True)

    seen2: set[tuple[str, str]] = set()
    while len(seen2) < 60:  # many more client names, in Greek and Latin letters, in business sentences
        full, short = rng.choice(CLIENTS2)
        form = rng.choice([full, short])
        tmpl = rng.choice(CLIENT2_EL if rng.random() < 0.45 else CLIENT2_EN)
        if (form, tmpl) in seen2:
            continue
        seen2.add((form, tmpl))
        add(tmpl.format(c=form), "CLIENT", form, "YES", "CLIENT_yes", "client_name", False)
    for span, s in CLIENT2_NO:
        add(s, "CLIENT", span, "NO", "CLIENT_no", "client_lookalike", True)
    for _lang, t, xs in SALARY_YES:
        for x in xs:
            add(t.format(x=x), "AMOUNT", x, "YES", "AMOUNT_yes", "salary_figure", False)
    for _lang, t, xs in AMOUNT_NO:
        for x in xs:
            add(t.format(x=x), "AMOUNT", x, "NO", "AMOUNT_no", "number_not_salary", True)
    for _ in range(30):  # random figures: pay in different formats (YES) against quantities and ids (NO)
        _lang, t, _xs = rng.choice(SALARY_YES)
        v = rng.randint(22, 78) * 1000 + rng.choice([0, 0, 500])
        x = rng.choice([f"{v:,} euros", f"€{v:,}", f"{v // 1000}k euros", f"{v:,}".replace(",", ".") + " ευρώ"])
        if _lang == "el" and not x.endswith("ευρώ"):
            x = f"{v:,}".replace(",", ".") + " ευρώ"
        add(t.format(x=x), "AMOUNT", x, "YES", "AMOUNT_yes", "salary_figure", False)
    for _ in range(110):  # random quantities and ids, each template gets the kind of number it expects
        n = rng.randint(6, 60)
        big = rng.randint(8, 48) * 1000 + rng.choice([0, 500])
        kinds = {
            0: lambda: f"{big:,}".replace(",", ".") + " λίτρα", 1: lambda: f"{n} παλέτες",
            2: lambda: rng.choice(["ISO 22000", "ISO 9001", "HACCP 2005"]), 5: lambda: str(rng.randint(1000, 9999)),
            6: lambda: f"{big:,} litres", 7: lambda: f"{n} pallets", 8: lambda: rng.choice(["ISO 22000", "ISO 9001", "HACCP"]),
            11: lambda: str(rng.randint(1950, 2015)), 12: lambda: f"no. {rng.randint(1000, 9999)}",
        }
        idx = rng.choice(list(kinds))
        _lang, tmpl, _xs = AMOUNT_NO[idx]
        x = kinds[idx]()
        add(tmpl.format(x=x), "AMOUNT", x, "NO", "AMOUNT_no", "number_not_salary", True)
    for _ in range(14):
        fg, fl, sg, sl = person()
        lang, t = rng.choice(PHONE_YES)
        p = f"69{rng.randint(0, 9)}0 00{rng.randint(0, 9)} {rng.randint(100, 999)}".replace(" ", "")
        add(t.format(n=(fg if lang == "el" else fl), p=p), "PHONE", p, "YES", "PHONE_yes", "phone", False)
    for _ in range(26):
        lang, t = rng.choice(PHONE_NO)
        p = f"69{rng.randint(0, 9)}0 00{rng.randint(0, 9)} {rng.randint(100, 999)}".replace(" ", "")
        add(t.format(p=p), "PHONE", p, "NO", "PHONE_no", "reference_number", True)
    return out


# ---------------------------------------------------------------- guards
def avoid_text(paths: list[Path]) -> str:
    texts = []
    for root in paths:
        files = [root] if root.is_file() else sorted(root.rglob("*")) if root.exists() else []
        for f in files:
            if f.is_file() and f.suffix in {".md", ".csv", ".yaml", ".yml", ".json", ".txt", ".py"}:
                texts.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(texts)


def check_disjoint(examples: list[dict], avoid_paths: list[Path]) -> list[str]:
    problems: list[str] = []
    text = avoid_text(avoid_paths)
    if not text.strip():
        problems.append("nothing found to compare against: " + ", ".join(map(str, avoid_paths)))
        return problems
    ftext = " ".join(toks(text))
    shingle6 = shingles(text, 6)
    for e in examples:
        blob = e["prompt"] + " " + json.dumps(e["cand"], ensure_ascii=False)
        hit = shingles(e["prompt"], 6) & shingle6 | shingles(e["cand"].get("chunk", ""), 6) & shingle6
        if hit:
            problems.append(f"6-word overlap with test data: {' '.join(next(iter(hit)))}")
    # names, companies and clients of the training company must not occur in the test data
    words = set(toks(text))
    in_test = [
        " ".join(toks(full))
        for first_g, first_l, _ in FIRST
        for sur_g, sur_l in SURNAMES
        for full in (f"{first_g} {sur_g}", f"{first_l} {sur_l}")
        if " ".join(toks(full)) in ftext
    ]
    for e in examples:
        folded = " ".join(toks(e["prompt"] + " " + e["cand"].get("span", "")))
        for full in in_test:
            if full in folded:
                problems.append(f"full name also in test data: {full}")
    for name in ["Taygetos", "Nordmarkt", "Evripos", "Baltic Delikatessen", "Messiniaki", "Kanakis"]:
        if " ".join(toks(name)) in ftext:
            problems.append(f"company or person also in test data: {name}")
    shared = sorted({sl for _, sl in SURNAMES if fold(sl) in words} | {sg for sg, _ in SURNAMES if fold(sg) in words})
    bad = [s for s in shared if fold(s) not in ALLOWED_SURNAME_OVERLAP]
    # Latin and Greek forms both count; allowed ones are the very common surnames only
    bad = [s for s in bad if fold(s) not in ALLOWED_SURNAME_OVERLAP and s not in {"Παπαδάκη", "Δήμου", "Κάλλη"}]
    if bad:
        problems.append("surnames shared with test data: " + ", ".join(bad))
    return problems


# ---------------------------------------------------------------- assemble
def dedup(examples: list[dict]) -> tuple[list[dict], int]:
    kept: list[dict] = []
    sigs: list[tuple[set, str]] = []
    dropped = 0
    for e in examples:
        key = e["cand"].get("chunk") or e["cand"]["category"]
        sg = shingles(e["prompt"], 3) or {tuple(toks(e["prompt"]))}
        if any(k == key and jaccard(sg, s) >= 0.8 for s, k in sigs):
            dropped += 1
            continue
        sigs.append((sg, key))
        kept.append(e)
    return kept, dropped


def balance(examples: list[dict], rng: random.Random) -> list[dict]:
    """30% YES inside each candidate type (document chunks and entities separately).

    Balancing only overall let entities be about 47% YES against 24% for documents, so "it is an entity"
    would have been a shortcut to YES. Now neither type tells the model the answer.
    """
    out: list[dict] = []
    for ty in sorted({e["meta"]["type"] for e in examples}):
        pool = [e for e in examples if e["meta"]["type"] == ty]
        pos = [e for e in pool if e["verdict"] == "YES"]
        neg = [e for e in pool if e["verdict"] == "NO"]
        n_pos = min(len(pos), int(len(neg) * YES_SHARE / (1 - YES_SHARE)))
        n_neg = round(n_pos * (1 - YES_SHARE) / YES_SHARE)
        # the kinds the first test round got wrong (client names, surnames alone) are kept first, up to a cap
        first: list[dict] = []
        for sub in PRIORITY_SUBS:
            first += rng.sample([e for e in pos if e["meta"]["sub"] == sub],
                                min(PRIORITY_CAP, sum(e["meta"]["sub"] == sub for e in pos)))
        rest = [e for e in pos if e not in first]
        chosen = (first + rng.sample(rest, max(0, min(len(rest), n_pos - len(first)))))[:n_pos]
        out += chosen + rng.sample(neg, n_neg)
    rng.shuffle(out)
    return out


def split(examples: list[dict], rng: random.Random) -> tuple[list[dict], list[dict]]:
    groups: dict[tuple, list[dict]] = {}
    for e in examples:
        groups.setdefault((e["verdict"], e["meta"]["type"], language(e["prompt"])), []).append(e)
    train, val = [], []
    for k in sorted(groups):
        g = groups[k]
        rng.shuffle(g)
        n_val = max(1, round(len(g) * VAL_SHARE)) if len(g) > 1 else 0
        val.extend(g[:n_val])
        train.extend(g[n_val:])
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def augment_split(rows: list[dict], rng: random.Random) -> list[dict]:
    """Rewrite AUG_SHARE of each class (same share of YES and NO, so 30/70 holds) inside one split."""
    out: list[dict] = []
    for verdict in ("YES", "NO"):
        pool = [e for e in rows if e["verdict"] == verdict]
        for i, e in enumerate(rng.sample(pool, round(len(pool) * AUG_SHARE))):
            kinds = judge_aug.KINDS_ENTITY if e["cand"]["type"] == "entity" else judge_aug.KINDS_DOC
            for k in range(len(kinds)):  # next kind if this one changes nothing (Greeklish on English text)
                a = judge_aug.augment(e, kinds[(i + k) % len(kinds)], rng, language)
                if a:
                    out.append(a)
                    break
    public = [e for e in rows if e["meta"].get("sub") == "public_doc"]  # capitals and Greeklish of public text must stay NO
    for e in rng.sample(public, len(public) // 2):
        kinds = judge_aug.KINDS_DOC
        i = rng.randrange(len(kinds))
        for k in range(len(kinds)):
            a = judge_aug.augment(e, kinds[(i + k) % len(kinds)], rng, language)
            if a:
                out.append(a)
                break
    return out


def to_row(e: dict) -> dict:
    user = build_input(e["prompt"], e["cand"])
    model = build_output(e["verdict"], e["reason"])
    meta = {k: v for k, v in e["meta"].items() if k != "hard"}
    meta.update(hard=bool(e["meta"].get("hard")), lang=language(e["prompt"]))
    return {
        "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": model}],
        "text": gemma_text(user, model),
        "meta": meta,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def stats_md(train: list[dict], val: list[dict], dropped: int, max_sim: float, pool: int) -> str:
    allrows = [(e, "train") for e in train] + [(e, "val") for e in val]
    n = len(allrows)

    def table(title: str, keyf) -> list[str]:
        c: Counter = Counter()
        for e, part in allrows:
            c[(keyf(e), e["verdict"], part)] += 1
        keys = sorted({k for k, _, _ in c})
        lines = [f"### {title}", "", "| value | YES | NO | train | val | total |", "|---|---|---|---|---|---|"]
        for k in keys:
            y = c[(k, "YES", "train")] + c[(k, "YES", "val")]
            no = c[(k, "NO", "train")] + c[(k, "NO", "val")]
            tr = c[(k, "YES", "train")] + c[(k, "NO", "train")]
            va = c[(k, "YES", "val")] + c[(k, "NO", "val")]
            lines.append(f"| {k} | {y} | {no} | {tr} | {va} | {y + no} |")
        return lines + [""]

    yes = sum(1 for e, _ in allrows if e["verdict"] == "YES")
    hard = sum(1 for e, _ in allrows if e["meta"].get("hard"))
    greek = sum(1 for e, _ in allrows if language(e["prompt"]) == "el")
    lines = [
        "# Fine-tune data for the D7 judge",
        "",
        "Made by `scripts/gen_finetune.py` (seed 42) from the invented company in `data/train_org/`. "
        "Nothing here comes from `data/org`, `data/documents` or `data/eval`; the script fails if it finds an overlap.",
        "",
        f"- Examples: **{n}** (train {len(train)}, val {len(val)}); generated {pool} before balancing, {dropped} near-duplicates dropped",
        f"- YES **{yes}** ({yes / n:.1%}), NO **{n - yes}** ({(n - yes) / n:.1%}); target 30 / 70",
        f"- Hard negatives (same-topic, public, look-alike words, numbers that are not salaries): **{hard}** = {hard / n:.1%} of all examples (rule: at least 50%)",
        f"- Greek prompts: **{greek}** = {greek / n:.1%} (rule: at least 40%)",
        f"- Highest word-overlap (Jaccard, 3-word shingles) between a validation prompt and a training prompt on the same candidate: {max_sim:.2f}",
        "",
    ]
    lines += table("By candidate type", lambda e: e["meta"]["type"])
    lines += table("By language of the prompt", lambda e: language(e["prompt"]))
    lines += table("By rewrite (label-preserving augmentation)", lambda e: e["meta"].get("aug", "none"))
    lines += table("By kind of example", lambda e: e["meta"]["sub"])
    lines += table("By source document or entity category", lambda e: e["meta"].get("doc") or e["meta"].get("category"))
    lines += [
        "Hard negatives by kind: " + ", ".join(
            f"{k} {v}" for k, v in sorted(Counter(e["meta"]["sub"] for e, _ in allrows if e["meta"].get("hard")).items())),
        "",
        "## Format",
        "",
        "Each line of `train.jsonl` / `val.jsonl` has `messages` (user turn = instruction + PROMPT + CANDIDATE, "
        "assistant turn = the JSON; the Gemma template maps `assistant` to its `model` turn), `text` (the same in "
        "native Gemma markers, for trainers that take one column) and `meta` (kind, language, hard flag; drop it before training).",
        "",
    ]
    return "\n".join(lines)


AVOID_FOLDED = ""


def main() -> None:
    global AVOID_FOLDED
    ap = argparse.ArgumentParser()
    ap.add_argument("--avoid", action="append", default=[], help="extra test-data folders or files to keep clear of")
    args = ap.parse_args()
    rng = random.Random(SEED)
    AVOID_FOLDED = " ".join(toks(avoid_text(DEFAULT_AVOID + [Path(p) for p in args.avoid])))

    pool = doc_examples(rng) + entity_examples(rng)
    pool_n = len(pool)
    pool, dropped = dedup(pool)
    chosen = balance(pool, rng)

    problems = check_disjoint(chosen, DEFAULT_AVOID + [Path(p) for p in args.avoid])
    yes = sum(e["verdict"] == "YES" for e in chosen) / len(chosen)
    hard = sum(bool(e["meta"].get("hard")) for e in chosen) / len(chosen)
    greek = sum(language(e["prompt"]) == "el" for e in chosen) / len(chosen)
    if not 0.29 <= yes <= 0.31:
        problems.append(f"YES share {yes:.3f} is not about 30%")
    if hard < 0.5:
        problems.append(f"hard negatives are {hard:.1%}, need at least 50%")
    if greek < 0.4:
        problems.append(f"Greek prompts are {greek:.1%}, need at least 40%")
    if problems:
        print("\n".join(sorted(set(problems))[:40]), file=sys.stderr)
        sys.exit(1)

    train, val = split(chosen, rng)
    max_sim = 0.0
    tsig = [(shingles(e["prompt"], 3), e["cand"].get("chunk") or e["cand"]["category"]) for e in train]
    for e in val:
        k = e["cand"].get("chunk") or e["cand"]["category"]
        sg = shingles(e["prompt"], 3)
        for s, tk in tsig:
            if tk == k:
                max_sim = max(max_sim, jaccard(sg, s))
    train = train + augment_split(train, rng)
    val = val + augment_split(val, rng)
    rng.shuffle(train)
    rng.shuffle(val)
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "train.jsonl", [to_row(e) for e in train])
    write_jsonl(OUT / "val.jsonl", [to_row(e) for e in val])
    (OUT / "stats.md").write_text(stats_md(train, val, dropped, max_sim, pool_n), encoding="utf-8")
    print(f"train {len(train)}, val {len(val)}, YES {yes:.1%}, hard {hard:.1%}, Greek {greek:.1%}, dropped {dropped}")


if __name__ == "__main__":
    main()
