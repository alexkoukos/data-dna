# Why employees will prefer it (T5)

A control people route around fails. The gate has to be the easier way to use AI. Five reasons, each tied to something in the repo. They are hypotheses until we test them with users (the nightly first-time-user test in `docs/IDEA_AND_TEAM.md`).

1. **It answers, it does not just refuse.** Confidential questions go to the local model, so the person gets a useful answer instead of a block.
2. **Nothing to worry about.** Secrets and identifiers are masked before leaving and put back in the answer, so people do not have to clean their text first.
3. **It explains itself.** Every outcome has a one-line reason and a "Why?" panel in plain words, plus the approved alternative.
4. **A safer version in one click.** On a warning, the safe rewrite button gives text that can be sent; the dashboard counts how often it is accepted.
5. **Good models without a personal account.** The company chat reaches strong models through the company's key (when one is configured; without it the local model answers), so staff need no personal subscription.

What to measure in a pilot: share of messages allowed unchanged, acceptance of the safe rewrite, and whether use moves from unapproved tools to the gate (the tool inventory shows this).
