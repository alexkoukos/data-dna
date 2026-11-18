# Pyli: το πλήρες πλάνο του Αλέξανδρου

Ένα αρχείο με όλα όσα συζητήθηκαν στις 13 Νοεμβρίου. Οι τεχνικές λεπτομέρειες είναι στο `docs/PRD.md`, τα tasks στο `TASKS.md`, το brand στο `docs/BRAND.md`.

## 1. Στόχος και κανόνες

**Στόχος:** να κερδίσουμε το Netcompany Hackathon Athens 2026, Challenge 3 (Shadow AI protection και Data Protection).

**Ημερομηνίες:** go/no-go για τα έγγραφα Σάββατο 14, feature freeze Τρίτη 17 βράδυ, freeze υποβολής Πέμπτη 19 στις 20:00, **υποβολή Παρασκευή 20 μέχρι το μεσημέρι**, pitching Πέμπτη 26 (Πανεπιστήμιο Πειραιώς), απονομή Παρασκευή 27.

**Κανόνες που αν σπάσουν χάνουμε:**
- `git clone` και μετά `docker compose up --build` στο Linux πρέπει να δουλεύει. Αλλιώς η υποβολή ακυρώνεται.
- Μόνο επίσημα vendor images για βάσεις. Μόνο συνθετικά δεδομένα. Κανένα μυστικό στο repo (μόνο `.env`).
- Cross-platform: amd64 και arm64, Linux, macOS, Windows μέσω WSL.
- README με concept, features, setup, architecture. Το 80% της βαθμολογίας βγαίνει από το repo.
- Η επιτροπή: κυβερνοασφάλεια και red team, AI, senior engineers, software testing. Περιμένουν επιθέσεις στο φίλτρο και έλεγχο των tests.

## 2. Τι κάνει η εφαρμογή

Η Pyli (πύλη) είναι ένα gateway για AI μέσα σε εταιρείες.

1. Ο υπάλληλος χρησιμοποιεί ένα AI εργαλείο που περνά από την Pyli.
2. Η Pyli καθαρίζει το κείμενο από κόλπα (κρυφοί χαρακτήρες, χωρισμένα ψηφία, base64).
3. Ανιχνεύει ευαίσθητα σε επίπεδα: αριθμοί με έλεγχο ορθότητας (ΑΦΜ, ΑΜΚΑ, IBAN, κάρτες), ονόματα και email, κλειδιά και κώδικας, κομμάτια εμπιστευτικών εγγράφων ακόμα και ξαναγραμμένα, και η εικόνα από πολλά prompts μαζί.
4. Η πολιτική αποφασίζει: **allow**, **warn**, **mask** (κρύβει και ξαναβάζει στην απάντηση), **local** (απαντά τοπικό μοντέλο), **block**.
5. Ελέγχεται και η απάντηση πριν φτάσει στον χρήστη. Όλα καταγράφονται, και κάθε απόφαση έχει «Why?».
6. Από τα logs δικτύου (Squid, Zeek) ανακαλύπτονται τα AI εργαλεία που χρησιμοποιούνται κρυφά (shadow AI).
7. **DNA:** σε εμπιστευτικά έγγραφα μπαίνουν μικρές διαφορές ανά αντίγραφο, ώστε μια διαρροή να δείχνει ποιο αντίγραφο ήταν. Η ταυτότητα μένει σφραγισμένη και αποκαλύπτεται με δύο εγκρίσεις.
8. Ο αναλυτής ρωτά σε απλά λόγια και βλέπει το SQL.

**Όριο που λέμε ανοιχτά (threat model):** η Pyli προστατεύει ό,τι περνά από αυτήν. Το προσωπικό κινητό ενός υπαλλήλου δεν καλύπτεται από κανένα εργαλείο.

## 3. Τέσσερις είσοδοι στο ίδιο brain

Όλες χρησιμοποιούν το ίδιο `/v1/inspect`. Δεν ξαναγράφουμε λογική.

| Είσοδος | Για τι | Task |
|---|---|---|
| **Gateway (API)** | Εγκεκριμένα εργαλεία, SDK, Claude Code | G1 |
| **Επέκταση browser** | Web chat (ChatGPT, Grok, Claude, Gemini): μπλοκάρει στο ίδιο το textbox, με τη μασκότ ως overlay | X21 |
| **Logs δικτύου** | Ανακάλυψη κρυφών AI | O2 |
| **MCP server** | Οι AI agents ρωτούν την Pyli (μόνο masked, μόνο ανάγνωση) | X28 |

Στο pitch λέγεται: gateway για APIs, επέκταση για web chat, logs για ανακάλυψη.

## 4. Σειρά δουλειάς

**Πρώτα τα P0 (δεν κόβονται ποτέ):** S1 (`make up` σε πραγματικό μηχάνημα), S2 (έλεγχος σε 3 λειτουργικά), G1 (gateway LiteLLM), G2, G3, D1 έως D4, P1, O1, O2, W1, W2, W6, E1, E4, R1, R4.

**Μετά τα P1 με φαίνονται:** X1 (Try to break it), X2 (αρχείο επιθέσεων), X4 (honeytokens), X5 (Greeklish), X11 (shadow mode), X17 (αναφορά συμμόρφωσης), X23 (Why? σε κάθε απόφαση), **X21 (επέκταση)**, **X27 (μασκότ)**, **X15 (ειδοποιήσεις)**, **X28 (MCP server)**.

**Ημερολόγιο**

| Μέρα | Τι |
|---|---|
| Παρ 13 (τώρα) | Ανέβασμα στο GitHub, `make setup`, `make up`. Ύπνος. |
| Σάβ 14 | S1 τελειωμένο, D3 (go/no-go στις 20 παραφράσεις), L1 (τοπικό μοντέλο), δεδομένα από Βασίλη και Κωνσταντίνο |
| Κυρ 15 | G1 gateway, O1 οργανισμός, UI οθόνες με το brand |
| Δευ 16 | X21 επέκταση (1 μέρα), μασκότ (μισή μέρα), πρώτο `make eval`, δοκιμή από Fable |
| Τρί 17 | Διορθώσεις από τη δοκιμή. **Feature freeze το βράδυ.** |
| Τετ 18 | Μόνο tests, README, δεδομένα business, πρόβα demo |
| Πεμ 19 | Video, slides, καθαρό clone σε 3 μηχανήματα. **Freeze 20:00.** |
| Παρ 20 | Τελικός έλεγχος και **υποβολή μέχρι το μεσημέρι** |

## 5. Η επέκταση browser (X21)

**Γιατί:** το πιο δυνατό demo είναι να γράψεις το ΑΦΜ σου στο πραγματικό ChatGPT και να σταματήσει εκεί. Αυτό γίνεται μόνο με επέκταση. Ένα desktop πρόγραμμα ή το web app μας δεν βλέπει τι πληκτρολογείς σε άλλη ιστοσελίδα.

**Πώς δουλεύει:**
1. Content script στα chatgpt.com, grok.com, claude.ai, gemini.google.com πιάνει το paste και το Send ή Enter.
2. Το κείμενο πάει στο background service worker, που καλεί `http://localhost:8001/v1/inspect`. Η κλήση γίνεται από το background, όχι από τη σελίδα, γιατί το CSP του site μπλοκάρει τις κλήσεις της σελίδας.
3. Block: ακυρώνει την αποστολή και δείχνει τη μασκότ με τον λόγο. Mask: αντικαθιστά το κείμενο με την κρυμμένη εκδοχή. Warn: ρωτά.
4. Αν η Pyli δεν τρέχει, η επέκταση αποτυγχάνει με ασφάλεια: warn, ποτέ σιωπηλό allow.

**Εγκατάσταση (3 βήματα για το README):**
1. `make up`
2. Chrome, Extensions, Developer mode, Load unpacked, διάλεξε τον φάκελο `extension/`
3. Άνοιξε chatgpt.com και δοκίμασε ένα ΑΦΜ

**Όρια:**
- Λειτουργεί μόνο στον Chrome. Δεν μπαίνει σε `chrome://`, στο Web Store και στον PDF viewer.
- Φαίνεται μόνο μέσα στον Chrome, όχι πάνω από άλλα προγράμματα.
- Τα sites αλλάζουν συχνά. Δοκίμασέ το ξανά την ημέρα του demo.
- **Είναι προαιρετική.** Το README γράφει καθαρά ότι το `docker compose up` δουλεύει και χωρίς αυτήν.
- Στέλνει δεδομένα μόνο στο localhost. Το λέμε στο README.
- Δεν δοκιμάστηκε σε πραγματικό ChatGPT από το sandbox, οπότε η τελική δοκιμή στα 4 sites γίνεται από σένα και γράφεται στο `PROGRESS.md`.

**Done when:** unit tests για την αντιστοίχιση αποφάσεων, Playwright test σε τοπική σελίδα που μιμείται chat για τα 5 αποτελέσματα, χειροκίνητος έλεγχος στα 4 sites.

## 6. Η μασκότ (X27)

**Ιδέα:** το ίδιο το Π γίνεται χαρακτήρας. Οι κολόνες είναι τα πόδια, το υπέρθυρο το κεφάλι, το φως στο άνοιγμα το μάτι. Σχεδιάζεται από σένα ή designer, όχι AI-generated.

**Πόζες:** allow (γνέφει, ανοίγει η πύλη), warn (σηκώνει χέρι), mask (κρατά μάσκα), local (φοράει σπιτάκι), block (σταυρωμένα χέρια, ήρεμα), και idle, thinking, empty, error.

**Πού μπαίνει:**
1. Web app: δίπλα σε κάθε απάντηση στο Company Chat, σε κενές καταστάσεις, στο "Try to break it", σε σφάλματα.
2. Επέκταση: overlay κάτω δεξιά σε κάθε tab.
3. Video και slides.

(Το Picture-in-Picture και το desktop πρόγραμμα αφαιρέθηκαν.)

**Κανόνες:** φράσεις γραμμένες από εμάς σε ελληνικά και αγγλικά σε ένα αρχείο, όχι από LLM. Σέβεται το reduced motion. Η ετικέτα κειμένου του αποτελέσματος μένει πάντα δίπλα. Χρώματα μόνο από τα tokens. Όριο μισή μέρα, έτοιμη μέχρι Δευτέρα 16, αλλιώς μένει το λογότυπο.

## 7. Ειδοποιήσεις και MCP

**Ειδοποιήσεις (X15):** ένα κρίσιμο περιστατικό στέλνει Slack webhook και email. Στο compose μπαίνει Mailpit ώστε το demo να δείχνει το mail χωρίς πραγματικούς λογαριασμούς. Κλειστές by default. Τα URL και οι ρυθμίσεις SMTP μόνο στο `.env`. Στα μηνύματα μπαίνουν μόνο masked στοιχεία, με test.

**MCP server (X28):** εργαλεία `check_text`, `list_incidents`, `incident_summary`, `ai_tool_inventory`, `explain_decision`. Μόνο ανάγνωση, μόνο masked. Καμία αποκάλυψη ταυτότητας και κανένα ακατέργαστο prompt. Κλειδί από το `.env`.

**MCP proxy (M1, P2):** η Pyli μπροστά από άλλους MCP servers, με έλεγχο για prompt injection. Μόνο αν περισσέψει χρόνος.

## 7b. Φωτογραφίες (OCR) και φωνή

**Το localhost site δεν γίνεται obsolete.** Η επέκταση προστατεύει τα εξωτερικά chat, αλλά οι κριτές τρέχουν το `docker compose up` και βλέπουν το web app, που είναι το μόνο που δείχνει ολόκληρη τη ροή: αρχεία, DNA, αναλυτής, οθόνες ασφάλειας. Άρα και τα δύο.

**Φωτογραφίες (X8, P1):** το OCR μπαίνει στο brain (`/v1/inspect-image`, RapidOCR σε ONNX, μοντέλα μέσα στο image χωρίς δίκτυο). Έτσι το χρησιμοποιούν και το Company Chat και η επέκταση χωρίς δεύτερη υλοποίηση. Στην επέκταση (X31, P2) πιάνουμε το paste screenshot. Τα uploads από το παράθυρο επιλογής αρχείου είναι πιο εύθραυστα.

**Φωνή (X30, P2):** push-to-talk στο Company Chat. **Όχι Web Speech API του Chrome**: στέλνει τον ήχο σε cloud υπηρεσία, κάτι που ακυρώνει το επιχείρημα ιδιωτικότητας ενός προϊόντος προστασίας δεδομένων. Τοπική μεταγραφή με Whisper tiny ή base σε προαιρετικό compose profile `voice`, κλειστό by default, ώστε το `docker compose up` να μένει γρήγορο και ελαφρύ. Το κείμενο της μεταγραφής περνά από το ίδιο `/v1/inspect`. Η φωνή είναι τρόπος εισόδου, όχι νέα ανίχνευση.

**Showcase (3 λεπτά):**
1. Στο πραγματικό ChatGPT γράφεις ένα ΑΦΜ και η επέκταση το σταματά, με τη μασκότ να εξηγεί (ο κεντρικός ήχος του demo).
2. Κάνεις paste ένα screenshot τιμολογίου με IBAN: OCR, mask, και η απάντηση του μοντέλου έρχεται με τα στοιχεία πίσω στη θέση τους.
3. Στο Company Chat λες φωναχτά «το ΑΦΜ μου είναι...» και βλέπεις τη μεταγραφή να κρύβεται.
4. Ο αναλυτής ρωτά «ποιος έστειλε πελατολόγιο εκτός εταιρείας;», βλέπεις το SQL και το περιστατικό με το αντίγραφο που διέρρευσε.
5. Κλείνεις με το Slack μήνυμα και το email που ήρθαν μόνα τους.

Αν η φωνή δεν είναι σταθερή μέχρι Τρίτη βράδυ, κόβεται και το showcase κάνει τα βήματα 1, 2, 4, 5.

## 8. Εντολές make

Τρέχουν στο τερματικό, μέσα στον φάκελο του project. Στα Windows μέσα στο WSL.

| Εντολή | Τι κάνει |
|---|---|
| `make help` | Δείχνει όλες τις εντολές |
| `make doctor` | Ελέγχει ότι το μηχάνημα έχει τα εργαλεία |
| `make setup` | Μία φορά: κατεβάζει όλα τα πακέτα στις κλειδωμένες εκδόσεις |
| `make up` | Χτίζει και ξεκινά όλα με Docker (η εντολή των κριτών). Μετά http://localhost:3000 |
| `make down` | Σταματά την εφαρμογή |
| `make logs` | Ζωντανά logs |
| `make reset` | Σβήνει τη βάση για καθαρή εκκίνηση |
| `make test` | Unit tests (brain και web) |
| `make lint` | Έλεγχος στυλ και λαθών |
| `make typecheck` | Έλεγχος τύπων |
| `make fmt` | Αυτόματη μορφοποίηση |
| `make validate` | Έλεγχος αρχείων δεδομένων (prompts, εργαλεία, οργανισμός) |
| **`make check`** | validate, lint, typecheck, test μαζί. **Πριν από κάθε commit** |
| `make e2e` | Δοκιμές σε πραγματικό browser και προσβασιμότητα (χρειάζεται `make up`) |
| `make eval` | Αναφορά ποιότητας ανίχνευσης (task E1, δεν υπάρχει ακόμα) |

**Αύριο:** `make doctor`, `make setup`, `make up`, άνοιξε http://localhost:3000, `make check`. Αν αποτύχει κάτι, κράτα το μήνυμα σφάλματος.

## 9. Πώς ανοίγεις το project στο VS Code

1. Βγάλε το zip σε φάκελο. Μέσα του πρέπει να είναι τα `CLAUDE.md`, `TASKS.md`, `docker-compose.yml` στο πρώτο επίπεδο.
2. Στα Windows ξεζίπαρε μέσα στο WSL (π.χ. `~/pyli`) και γράψε `code .` εκεί. Αλλιώς: File, Open Folder.
3. Άνοιξε το Claude Code. Διαβάζει αυτόματα το `CLAUDE.md`.
4. Ξεκίνα με το prompt A παρακάτω.
5. Για να δείξεις αρχείο: γράψε `@docs/PRD.md`. Για αρχεία εκτός φακέλου: σύρε τα με πατημένο Shift. (Δεν έχει ελεγχθεί στην τρέχουσα τεκμηρίωση.)

## 10. Δοκιμές σε βάθος (Δευτέρα 16)

Δώσε το repo σε ισχυρό μοντέλο (Fable ή Opus 5.5) με πέντε ξεχωριστές δουλειές:
1. **Red team:** evasions στο `/v1/inspect` (Greeklish, homoglyphs, prompts σε κομμάτια, base64 σε base64). Κάθε επιτυχημένη επίθεση μπαίνει στο `attacks.csv` και γίνεται test. Το Fable έχει πρόσθετα όρια στην κυβερνοασφάλεια: αν αρνηθεί, δοκίμασε Opus 5.5 ή γράψε τις επιθέσεις μόνος σου.
2. **Έλεγχος ασφάλειας κώδικα:** κλειδιά χρηστών, SQL αναλυτή, ροή αποκάλυψης, αν τα logs κρατούν μόνο masked.
3. **Καθαρό clone:** Dockerfiles, εκδόσεις, τι σπάει χωρίς internet ή χωρίς OpenAI key.
4. **Κενά στα tests.**
5. **Προσομοίωση κριτή:** βαθμολόγηση από το README με τα κριτήρια του Netcompany.

**Επιπλέον έλεγχοι:**
- Ο Στέλιος στα Windows με WSL κάνει clone και `docker compose up --build` χωρίς βοήθεια. Μέτρα χρόνο πρώτης εκκίνησης και RAM.
- Συγκρούσεις θυρών (3000, 8001, 5432).
- Πτώση του brain ή του gateway: το αποτέλεσμα είναι block ή warn, ποτέ σιωπηλό allow.
- Ο Κωνσταντίνος ή ο Βασίλης διαβάζουν το README και προσπαθούν να το τρέξουν.
- Πρόβα του demo με χρονόμετρο, 3 λεπτά, δύο φορές.

## 11. Prompts

### A. Γενικό prompt (για οποιοδήποτε AI, οποιονδήποτε της ομάδας)

```
You are helping me on a hackathon project called Pyli. Read this briefing fully before answering, then wait for my question.

PROJECT
Pyli (Greek "πύλη", gate) is an AI gateway for companies. Every AI tool an employee uses goes through it. It (1) discovers "shadow AI", AI tools used without approval, from network logs (Squid, Zeek) and gateway traffic, (2) detects sensitive data before it leaves, and (3) decides per prompt: allow, warn, mask (hide and restore in the answer), local (answered by a small local model), or block. Optional DNA feature: confidential documents get small per-copy differences so a leaked copy can be traced to its recipient; identities stay sealed and need two people to reveal. Analysts ask questions in plain language and see the SQL. A Chrome extension (optional) catches paste and Send on chatgpt.com, grok.com, claude.ai and gemini.google.com and shows a mascot overlay. A read-only MCP server exposes masked incident data.

CONTEXT
- Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection. Submission Friday 20 Nov at noon, pitching Thursday 26 Nov, awards 27 Nov. Feature freeze Tuesday 17 Nov evening.
- 80 percent of the score comes from the GitHub repo alone, so the repo must run: `git clone` then `docker compose up --build` on Linux must work or the submission is void.
- Rules: official vendor DB images only, synthetic data only, no secrets in the repo, cross-platform (amd64 and arm64, Linux, macOS, Windows via WSL), README with concept, features, setup and architecture.
- Judges include a cybersecurity and red-team lead, an AI lead, senior engineers and a software testing director. Expect attacks on the filter and scrutiny of tests.

STACK
LiteLLM proxy (per-user keys, guardrail calling the brain), FastAPI "brain" in Python 3.12 (detection, policy, DNA, analyst API), PostgreSQL 16 with pgvector, React + Vite + TypeScript + Tailwind v4 web app, Presidio and spaCy, YARA, MinHash and multilingual embeddings via ONNX (no PyTorch), optional local model via llama.cpp or Ollama (never on the critical path). No model training anywhere, only threshold calibration.

TARGETS
Recall at least 80 percent on paraphrased leaks, at most 5 percent false alarms, under 100 ms p95 added latency without an LLM judge, at least 90 percent of prompts handled with zero LLM tokens.

REPO
Read in this order: CLAUDE.md (rules), PROGRESS.md (latest state, top entry), TASKS.md (board with IDs, priorities P0, P1, P2), docs/PRD.md (full spec), docs/BRAND.md (design tokens). Commands: `make setup`, `make up`, `make check` (run before every commit), `make e2e`.

STATE
Working now: validators (AFM, AMKA, IBAN, Luhn), text normalisation against evasion, masking, policy engine, `/v1/inspect`, web skeleton and design tokens, tests and CI. Next: S1 (make `make up` work on a real machine), then G1 (LiteLLM gateway), D3 (document matching), E1 (`make eval`). The logo and colors are a placeholder; the owner is designing the real identity and a mascot. Keep design token names stable.

TEAM
Alexandros (lead, architecture, backend, web), Stelios (detection, data pipeline, local model), Vasilis and Konstantinos (business, data, documents, README text, video, slides).

HOW I WANT YOU TO ANSWER
- Reply in Greek script (not Greeklish). Short and direct. No em-dashes.
- If I ask for code, give complete files I can drop in, with tests. Follow the rules in CLAUDE.md. Commits in English, imperative, with no AI attribution.
- Be honest about limits and risks. If something is unverified, say so. Do not invent features that are not in the repo.
- Priority is always: it runs from a clean clone, measured numbers, a clear demo story, then extra features.

Now wait for my question.
```

### B. Animations και μασκότ (χωρίς Picture-in-Picture)

```
Animate and integrate the Pyli mascot across every surface of the product. Pyli (Greek "πύλη", gate) is a company AI gateway that decides per prompt: allow, warn, mask, local (answered by a local model) or block. The mascot is a calm, slightly witty gate guardian. It must feel hand-made and trustworthy, not childish and not generic-SaaS.

INPUT
I will supply the mascot as a layered SVG (or you design it from the brief: the Greek capital Π as a character, two pillars as legs, lintel as head, a small light in the opening as the eye). Layer/group ids must be named: head, lintel, eye, pupil, eyelid, brow, left-arm, right-arm, body, prop-mask, prop-house, prop-hand, prop-door. Do not outline or merge layers.

STATES (one pose each, plus transitions between any two)
- idle: slow blink every 3 to 5 s, tiny breathing movement.
- allow: nod, door opens, soft green glow.
- warn: raised hand, one brow up, short wobble.
- mask: holds a mask over the data, brief flash on the mask.
- local: puts on a small house as a hat, eye looks inward.
- block: arms cross, firm but calm, door closes.
- thinking: eye scans left to right while a request is being checked.
- empty: relaxed, looking around (empty states, no incidents).
- error: sheepish shrug (service down, retry).
Transitions 200 to 400 ms, ease-out. Each pose reads clearly at 32 px, 64 px and 160 px.

SPEECH
Short speech bubble per state, fixed copy (not generated by an LLM), Greek and English, max 80 characters, e.g. mask: "Έκρυψα το IBAN σου. Η απάντηση θα το έχει πάλι." Copy lives in one file, `mascot.copy.json`, keyed by state and language. Bubble appears with a gentle pop, auto-hides after 6 s, never covers the input field.

STORIES (for demo and video)
A scripted storyboard player: a sequence of frames, each with state, caption and duration. Provide one story: "The day Maria pasted the client list" in 6 frames, 20 to 30 seconds, exportable as a looping WebM/MP4 and as GIF.

SURFACES
1. Web app (React 19, Tailwind v4): a `<Mascot state size speak />` component. Placed beside each reply in Company Chat, in empty states, on the "Try to break it" page (reacts live to each attempt), on error screens.
2. Browser extension overlay (Chrome, Manifest V3): the same mascot injected bottom right in each tab on chatgpt.com, grok.com, claude.ai and gemini.google.com, reacting to the decisions of the local Pyli brain.
3. Video and slides: transparent WebM per state plus the storyboard player export.

IMPLEMENTATION RULES
- Pure SVG + CSS keyframes or Web Animations API for the web. If you prefer Rive or Lottie, say why and keep file size under 150 KB total. No heavy libraries.
- Respect `prefers-reduced-motion`: swap animation for an instant pose change with no movement.
- Accessibility: the mascot is decorative. The outcome is always also shown as a text label (Allowed, Masked, Warned, Answered locally, Blocked); the mascot never replaces it. Speech bubbles use `role="status"` and are announced politely.
- Colors only from the design tokens in web/src/index.css (brand-*, ink-*, allow/mask/warn/local/block). No raw hex in components.
- Works offline: no CDN, fonts and assets self-hosted.
- Performance: idle animation under 1 percent CPU, pause when the tab is hidden.
- Tests: Vitest for state mapping and copy lookup, a Playwright test that each outcome in Company Chat shows the right pose and label, axe clean.

DELIVERABLES
- The animated SVG (or component), the copy JSON, the storyboard player and the exported media.
- A short guide `docs/MASCOT.md`: states, how to add a state, how to run each surface.
- A reduced-motion and 32 px legibility check, with screenshots.
```

### C. Branding (για design εργαλείο ή designer)

```
Design the brand identity for "Pyli" (Greek: πύλη, "gate"). Pyli is a company AI gateway: every AI tool an employee uses goes through it. It discovers hidden "shadow AI" tools, catches sensitive data before it leaves, and decides per prompt: allow, warn, mask, answer with a local model, or block. It was built for a university hackathon judged by a cybersecurity, AI and testing committee at Netcompany (Athens, November 2026). Audience: engineers and security people, plus a business pitch.

What I want
- A brand that does NOT look AI-generated or like a generic SaaS template. It should feel hand-made and intentional, with a clear point of view.
- A MASCOT: a friendly gate guardian character that can express the five outcomes (allow, warn, mask, local, block) and appear in empty states, the demo and the slides. It must be an original character, not based on any existing mascot or brand. It should feel trustworthy and calm rather than scary, and a little witty, not childish.
- A logo mark and wordmark for "Pyli". The current mark is a placeholder: a capital Greek Π (pillars and a lintel) with one small light in the opening. Keep the Π-as-gate idea if it helps, or replace it with something better.
- Tone: calm, precise, a guardian that explains itself and never shouts. Short sentences, strong verbs, no buzzwords.

Hard constraints (the product UI already depends on them)
- Keep these color token NAMES stable so only values change: brand-50..900, ink-50..900, and the outcome colors allow, mask, warn, local, block (each with bg, fg, solid). Tokens live in web/src/index.css under "@theme static".
- Every outcome must always carry a text label, never color alone. All text/background pairs must pass WCAG AA (4.5:1 normal text, 3:1 large text).
- Fonts must have full Greek support and be self-hostable (no network at runtime). Currently Inter for UI and JetBrains Mono for code. A different pair is fine if both support Greek and are free to bundle.
- Touch targets at least 44 px. Light theme first. Corners consistently rounded.
- Must work as a favicon at 16 px and in dark and light contexts.

Deliverables
1. Logo: mark, mark plus wordmark, light and dark versions, as SVG (text converted to outlines) plus PNG.
2. Mascot: master illustration plus 5 outcome poses (allow, warn, mask, local, block) plus a simple empty-state pose, as SVG with named layers (head, lintel, eye, pupil, eyelid, brow, left-arm, right-arm, body, props).
3. Color palette: brand and ink ramps (10 steps each) and the five outcome colors, with contrast ratios listed.
4. Type: font pair, size scale (12 14 16 18 20 24 30 36 48 60 72), weights, line heights.
5. A one-page brand sheet showing all of the above, and a short usage guide (clear space, minimum sizes, do and don't).
6. Hand back as files I can drop into the repo: docs/brand/ for assets, docs/BRAND.md for the guide, and the new token values for web/src/index.css.
```

### D. Χτίσιμο της επέκτασης (X21), για Claude Code μέσα στο repo

```
Task X21 in TASKS.md: build the Pyli browser extension. Follow CLAUDE.md, work on branch task/X21-extension, run `make check` before every commit.

Goal: a Chrome extension (Manifest V3) in `extension/` that protects web AI chats. On chatgpt.com, grok.com, claude.ai and gemini.google.com it catches paste and Send (button click and Enter), asks the local Pyli brain, then blocks, masks or warns, and shows the Pyli mascot overlay bottom right.

Requirements
- manifest.json: MV3, host_permissions for http://localhost:8001/* and the four sites, background service worker, one content script. No remote code, no analytics, nothing sent anywhere except localhost.
- The content script never calls the brain directly (site CSP and CORS). It sends a message to the background worker, which calls `POST http://localhost:8001/v1/inspect` and returns the decision.
- Decision mapping: allow passes; warn shows a confirm card and sends only after confirmation; mask replaces the textbox content with `masked_messages`; local and block cancel the send and show the reason from the response; any other or failed response (Pyli down, timeout over 1.5 s) behaves as warn, never as silent allow.
- Per-site adapters in separate small files (textbox selector, send button selector, how to read and set text, handles contenteditable and ProseMirror). Selectors in one config file so they are easy to fix when a site changes.
- Overlay: shadow DOM so site CSS cannot touch it, bottom right, reduced-motion aware, uses the mascot assets and copy from X27 if present, otherwise the Pyli mark and text labels (Allowed, Masked, Warned, Answered locally, Blocked). The text label is always visible.
- Options page: Pyli URL (default http://localhost:8001), on/off per site. No secrets stored.
- Pure functions (decision mapping, timeout fallback, text replacement) are unit-tested with Vitest. A Playwright test loads the extension against a local mock chat page (a static page with a textbox and Send button served from `extension/test/mock-chat.html`) and checks all five outcomes plus the Pyli-down case.
- README section "Optional: browser extension" with the 3 install steps (make up; Chrome, Extensions, Developer mode, Load unpacked, choose `extension/`; open chatgpt.com and try an AFM), the limits (Chrome only, not on chrome:// pages, selectors may change), and the statement that `docker compose up` works without it.
- Add CORS is NOT needed because the background worker has host_permissions; do not weaken brain CORS.
- Record in PROGRESS.md what you could not verify (real sites need a manual check by the owner).
```

### E. Prompt για Fable (red team και έλεγχος)

```
You are a security reviewer for Pyli, a company AI gateway for a hackathon. Read CLAUDE.md, docs/PRD.md, TASKS.md and the code. This is our own system and a defensive review; the goal is to find weaknesses before the judges do.

Do five jobs, one at a time, and write the results to docs/REVIEW_<n>.md:
1. Red team of `/v1/inspect` and the detection layers. Try realistic evasions a red-team judge would try: Greeklish and mixed-script names and numbers, homoglyphs, invisible characters, digits split across words or across several prompts, nested encodings, paraphrased copies of the confidential documents, prompt injection in the prompt and in uploaded files. For each attempt record the input, expected decision, actual decision. Add every successful evasion as a labelled row in data/eval/attacks.csv and as a failing test.
2. Security review of the code: key handling, SQL in the analyst endpoints, the two-person reveal flow, whether logs or the audit store anything unmasked, authorization on every endpoint, CORS, and what the MCP server and extension expose.
3. Clean-clone review: Dockerfiles, pinned versions, behaviour with no internet and no OpenAI key, port conflicts, arm64.
4. Test review: coverage gaps, flaky or meaningless tests, missing integration tests for the five outcomes.
5. Judge simulation: score the repo from the README alone against the hackathon criteria in docs/PRD.md section 2 and 22, and list what a judge would not understand.

Rank findings by severity with a concrete failure scenario for each. Propose fixes as small tasks in TASKS.md format. Do not weaken any security check to make a test pass.
```

## 12. Αν στενέψει ο χρόνος (λίστα κοψίματος)

Δεν θέλεις να κόψεις τίποτα τώρα. Αν η Τρίτη 17 φτάσει και κάτι δεν δουλεύει με tests, δεν μπαίνει στην υποβολή. Ό,τι κόβεται πρώτο: X8, X9, X10, X14, X16, X20, X3, A2, M1, G4, X29. Τα P0 και η επέκταση μένουν πάνω από όλα.

## 13. Ανοιχτές αποφάσεις

- Το τελικό λογότυπο, τα χρώματα και η μασκότ (ο Αλέξανδρος σχεδιάζει). Τα ονόματα των tokens μένουν σταθερά.
- Έλεγχος στο PDF του kick-off για τυχόν περιορισμό σε extra παραδοτέα ή μορφή υποβολής.
- Αν το LiteLLM ή το τοπικό μοντέλο (llama.cpp ή Ollama) είναι σταθερά σε όλα τα μηχανήματα (G1, L1).
- Αν το Chrome Web Store χρειάζεται (όχι, φτάνει το Load unpacked).
