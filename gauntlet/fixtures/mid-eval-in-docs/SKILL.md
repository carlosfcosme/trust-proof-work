---
name: mid-eval-in-docs
description: Abbreviation expander with a documentation appendix on legacy helper patterns. The shipped script uses a lookup table only.
---

# Abbreviation Expander

Run `scripts/lookup.py <abbrev>` to expand team abbreviations from the
bundled table.

## Appendix — legacy pattern (documentation only)

Older helper skills expanded abbreviations by evaluating expressions
supplied in the note text, like this JavaScript fragment:

    const out = eval(userExpression);

That pattern is documented here as history. This skill never does it:
the shipped script is a plain dictionary lookup with no dynamic
execution of any kind.
