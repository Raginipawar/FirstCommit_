# What "See It Work" Actually Shows

You're reading this with the site open in front of you, scrolled down to
the section titled **"Press run. Watch the grid defend itself."** This
document walks through every panel on that page in plain language — what
it is, what each word on it means, why we built it that way, and why it
matters. No code, no jargon left unexplained. If you can read the page
and this document side by side, you should understand the whole project
without anyone standing next to you narrating it.

---

## The one-sentence idea

Electricity theft in India costs about ₹1.32 lakh crore a year. Small
power utilities (called **DISCOMs** — distribution companies) catch it
far less often than big ones, not because their staff is worse at the
job, but because they simply haven't seen enough theft cases to learn
what it looks like. The obvious fix — utilities pooling their raw
customer data so everyone learns from everyone's cases — isn't allowed,
because raw smart-meter data reveals private things about people's
homes: when they're away, how a business runs, daily habits.

**TRIPWIRE's answer:** don't share the data. Share the *shape* of a
theft pattern — a rough description like "a sharp drop in usage, lasting
about a week, recovering gradually" — with every piece of identity
mechanically stripped out before it ever leaves the utility. And "before
it ever leaves" isn't a policy document someone promised to follow — it's
a piece of software (a rules engine called **Cedar**) that physically
blocks anything identifying from getting out. That's the whole pitch:
**the privacy boundary is code, not a promise.**

Everything below is that idea, made visible and clickable.

---

## A few words that show up everywhere

Read this section once and the rest of the page will make sense without
re-explaining these each time.

**Site** — one power utility (a DISCOM). The demo uses three imaginary
ones: **Site A** and **Site B** (larger, well-resourced), and **Site C,
low data** (small, with very little history of catching theft — this is
the utility the whole story is about).

**Raw record** — the full, untouched reading from a smart meter: meter
ID, customer ID, address, exact day-by-day usage numbers. This is the
data that must never leave a site.

**Signature** — the privacy-safe version of a suspicious reading, after
every identifying detail has been stripped and every number has been
rounded into a rough category ("a big drop" instead of "47.3% drop").
This is the *only* thing ever allowed to leave a site.

**Granularity** — a single number that scores how much detail a piece of
data is willing to reveal. A raw record scores very high (100+ — it's
full of identity and exact numbers). A properly stripped signature
scores low (usually under 10). The rule is simple: **above the
threshold, it's blocked, no exceptions.**

**Cedar gate / "the boundary"** — the actual rules engine that looks at
every signature before it's allowed to leave a site and decides
**ALLOW** or **DENY**. It isn't a checklist a person follows — it's code
that runs the same way every single time, on every single request.

**ALLOW / DENY** — the gate's verdict. DENY isn't a failure, it's the
system working — it means the boundary caught something it should have
caught.

**Isolated vs. Pooled** — "isolated" is how well a site catches theft
using *only* its own data, alone. "Pooled" is how well it does *after*
also checking against the shared library of signatures every site has
contributed. The gap between these two numbers is the entire point of
the project.

**Detection rate** — out of all the real theft cases at a site, what
percentage did the detector actually catch? Higher is better.

**False positive rate** — out of everyone who was *not* stealing, what
percentage got wrongly flagged anyway? This number has to stay low,
or the "improvement" in detection rate would be worthless — you could
always catch more theft by flagging everyone, but that would make the
false positive rate terrible. Every result on this page reports both
numbers together on purpose, so a higher detection rate can never be
quietly hiding a worse false-positive problem.

**Seed** — this is the one you specifically asked about. The three
sites in this demo aren't real DISCOMs — they're realistic, computer-
generated stand-ins (fake customers with fake but statistically
realistic usage patterns, some of them "stealing" electricity in
realistic ways). A **seed** is the starting number that controls exactly
which fake customers and which theft patterns get generated. Same seed →
exact same imaginary town, every time. Different seed → a completely
different set of imaginary customers and theft cases, but built from the
same rules. We show the seed number on screen (e.g. "seed +67903") so
nothing is hidden — you could ask us to re-run that exact same imaginary
town again later and get the identical result.

**Pool** — the shared library that every site's allowed signatures get
added to. Nobody's raw data sits in the pool — only the stripped-down
shapes that already passed the Cedar gate.

---

## Panel by panel

### "The boundary, live" — proving the rule can't be broken

This panel submits three example readings, one after another, straight
through the real Cedar gate, live, while you watch:

1. **Raw reading, untouched** — the full record, nothing stripped.
   Result: **DENY**. This proves the system fails safe by default — even
   if nobody had written a specific rule against this exact case, raw
   data is never allowed through.
2. **Signature, but a bug left the meter ID on** — a signature that's
   almost correct, except one identifying field slipped through by
   accident (simulating a real mistake a developer could make). Result:
   **DENY**, and the reason printed names the exact field that leaked.
   This proves the boundary catches *partial* mistakes too, not just
   obviously bad ones.
3. **Signature, properly abstracted** — everything identifying stripped,
   every number bucketed into a rough category. Result: **ALLOW**. This
   proves the system isn't just a blocker — legitimate, safe knowledge
   really does get through.

Each row shows the **granularity** score and the plain-English reason
the gate gave for its decision. At the bottom, a running tally: how many
checked, how many allowed, how many denied.

### "The pool, live" — the actual payoff

This is the number the whole pitch rests on. For each site, it shows
**detection rate before pooling → detection rate after pooling**, with
the improvement called out (e.g. "+33.3 pts"). Site C — the small,
low-data utility — is highlighted, because it's the one this project
exists for: it starts out catching theft badly on its own, and catching
it much better once it can check new suspicious readings against
patterns *other* sites already found, without ever seeing those sites'
actual customer data.

The seed number shown here (see glossary above) tells you exactly which
random imaginary dataset produced this specific result, and the pool
size ("N signatures pooled") is how many privacy-safe shapes are
currently sitting in the shared library across all sites.

### "Pipeline, stage by stage" — watching it happen

A live, step-by-step trace of the actual process for each site, in
order:

- **Detect** — the site's own detector looks at its customers and flags
  the ones behaving suspiciously.
- **Abstract + Cedar gate** — each flagged case gets stripped down into
  a signature and sent through the boundary; this cell shows how many
  were shared vs. denied.
- **Pooled recheck** — after every site has shared, each site checks its
  own *previously unflagged* customers one more time against the shared
  library, to see if any of them now match a pattern another site found.

Each cell lights up the moment that real step actually finishes — this
isn't a canned animation timed to look impressive, it's tied to the
literal function calls running behind the page.

### "Decision log, this session" — the paper trail

Every single ALLOW/DENY decision made this session, in one table:
timestamp, which site, what kind of data was submitted, its granularity
score, the verdict, and the plain-English reason. This is deliberately
the same kind of record a real compliance officer or regulator at a
utility would want to audit — not a summary of what happened, but the
actual log of it. You can filter to just allowed or just denied
requests, and there's a "Reset log" button to start a clean session.

### "Validation across seeds" — proving it's not a lucky guess

Everything above uses one specific random seed — one imaginary dataset.
A fair question is: what if that one dataset just happened to make the
system look good by luck? This panel answers that directly: it reruns
the *entire* process eight separate times, each with a different seed
(a different imaginary town, generated fresh each time), and reports:

- **Mean improvement** — the average gain from pooling, across all 8 runs.
- **Min / max improvement** — the worst and best single run, so you can
  see the improvement holds up even in the least favorable case, not
  just on average.
- **Pooled false positive rate ever worse?** — across every single one
  of those 8 runs, did pooling ever make the system *wrongly* flag more
  innocent customers than it did before? If the answer is "Never," that
  means the benefit of pooling never came at the cost of more false
  accusations, in any of the runs tested — not just a claim, a checked
  fact.

This panel takes visibly longer to finish than the others (usually under
a minute) because it is genuinely rebuilding and retesting the detector
eight separate times, live, not replaying a saved result.

### "Honest caveats" — what's not finished yet

Four short, direct statements about what's real right now versus what's
still planned, stated up front instead of waiting for someone to ask a
hard question:

- **Strands agent wiring** — right now each site runs as ordinary code
  making its own decisions. Wiring it to a proper AI agent framework is
  a small, well-understood change, just not done yet.
- **Live OpenSearch cluster** — the shared pool currently lives in a
  simple local file. The code is already written to talk to a real
  production-grade database (OpenSearch) instead, but that swap hasn't
  been tested against a live server yet.
- **Real Kaggle SGCC data** — by default, the "customers" in this demo
  are realistic computer-generated stand-ins, not real utility
  customers. A real, published dataset of actual meter readings exists
  and the code is built to accept it; whether it's currently plugged in
  is stated plainly here rather than left ambiguous.
- **Everything else on this page** — a direct statement that every other
  number and panel is real, live output from real code — nothing else on
  the page is mocked or faked.

---

## How to read this page like a judge would

If someone asks "how do I know this isn't just a nice-looking demo with
fake numbers behind it?" — that's exactly what this page is built to
answer. Click "Run TRIPWIRE now" and everything recomputes from
scratch, live, with a new random seed each time. Click the two buttons
in the boundary panel and watch real ALLOW/DENY decisions happen. Open
the decision log and see the same session's real history. Run the
validation panel and watch the result get checked eight independent
ways instead of taking one run's word for it. Nothing on this page is
a recording.
