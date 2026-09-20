# TRIPWIRE — 2-Minute Live Demo Script

**Format:** screen-recording of the live website, you talking over it — no
slides. Q&A style throughout (ask, then answer). Total runtime: **2:00
exactly**. Implementation/tech-stack proof gets **60 seconds minimum**
(1:00–2:00), as required.

Read the **[SAY]** lines out loud, word for word or close to it. The
**[DO]** lines are what you click/scroll on screen at that exact moment
— rehearse the clicks so your hands are ahead of your mouth, not behind
it.

---

## 0:00 – 0:12 — The hook (12 sec)

**[DO]** Site is already open on the landing section. Just your face or
just the screen — don't scroll yet.

**[SAY]**
> "Quick question — how much do you think India loses every year to
> electricity theft? ₹1.32 lakh crore. And the gap between the
> best-performing utility at catching it and the worst? Forty-five
> percentage points."

---

## 0:12 – 0:30 — Why it happens (18 sec)

**[SAY]**
> "Why such a huge gap? Not because small utilities are worse at their
> job — they simply haven't seen enough real theft cases to learn what
> it looks like. So the obvious fix is: share data across utilities,
> right? Except raw smart-meter data reveals when someone's home is
> empty, how a business runs, private daily habits. Utilities legally
> can't hand that over. So what do you actually do?"

---

## 0:30 – 0:55 — The idea, proven live (25 sec)

**[DO]** Scroll to the **"See it work"** section. Point at the "The
boundary, live" panel.

**[SAY]**
> "You don't share the data — you share the *shape* of the pattern. And
> the line that decides what's 'just a shape' versus 'still private'
> isn't a rule someone promised to follow. It's code. Watch this."

**[DO]** Click through the block-then-pass demo (or point at it if
already run): raw reading → **DENY**, leaky signature → **DENY** with
the exact leaked field named, clean signature → **ALLOW**.

**[SAY]**
> "A raw reading — denied automatically. A signature with one identity
> field accidentally left on — still denied, and it tells you exactly
> which field leaked. Only a properly stripped signature gets through."

---

## 0:55 – 1:10 — The payoff number (15 sec)

**[DO]** Point at "The pool, live" panel, Site C row.

**[SAY]**
> "Here's the actual payoff. Site C — a small, low-data utility — alone
> catches about a third of its theft cases. Once it can check suspicious
> readings against what *other* sites already found, without ever
> seeing their raw data, that jumps to two-thirds."

---

## 1:00 – 2:00 — Implementation & why this proves it's real (60 sec — required minimum)

This is the half that separates you from every team that showed a slide
with a number on it.

**[DO]** Click **"Run TRIPWIRE now"** live, on camera.

**[SAY]**
> "Now let me show you why this isn't just a nice-looking demo. Every
> number you just saw is computed live, right now, in front of you.
> Behind this page: a real scikit-learn anomaly detector, and a real
> Cedar policy engine — the same rules language AWS itself uses for
> access control internally — running inside a Python FastAPI backend,
> streaming results to this React frontend over live server-sent
> events. Nothing is pre-recorded."

**[DO]** Point at the seed number that just changed (e.g. "seed
+67903") next to the pool size.

**[SAY]**
> "Notice that number changed. Every single click regenerates a brand
> new random dataset — a new seed, shown right here, on screen — so
> nobody can accuse us of quietly cherry-picking one lucky run."

**[DO]** Scroll to "Pipeline, stage by stage."

**[SAY]**
> "This isn't a canned animation either — each stage lights up the
> instant that real backend function actually finishes running for that
> site: detect, abstract, check the Cedar gate, then the pooled
> recheck."

**[DO]** Scroll to "Validation across seeds."

**[SAY]**
> "And we didn't stop at one run being lucky. Click this, and it reruns
> the *entire* pipeline eight independent times, with eight different
> random seeds, and proves the improvement holds every time — and that
> pooling never once made false positives worse."

**[DO]** Scroll to "Decision log, this session."

**[SAY]**
> "Every decision gets logged — a real audit trail, exactly what a
> DISCOM's compliance officer or a regulator would actually want to
> inspect."

**[DO]** Show the URL bar — the live AWS address, not localhost.

**[SAY]**
> "And this isn't running on my laptop for this recording — it's
> deployed right now, live, on AWS, at this address, reachable by
> anyone."

---

## Closing line (fold into the last few seconds, don't add extra time)

**[SAY]**
> "Share the pattern. Never the person. That's TRIPWIRE."

---

## Before you hit record — checklist

- [ ] Refresh the site once so the seed/pool numbers aren't stale from
      earlier testing.
- [ ] Have "Decision log" reset (click "Reset log") so it's not cluttered
      from your rehearsals.
- [ ] Close any other browser tabs/notifications — full-screen the
      browser.
- [ ] Do one full silent run-through of the clicks first, then one
      full run-through out loud with a timer, before the real take.
- [ ] Confirm your internet is stable — the swarm run and validation
      panel both hit the live backend; a lag mid-recording will eat
      your 2 minutes.
- [ ] Speak slightly slower than feels natural — screen recordings and
      demo excitement both make people talk faster than they think.

## Timing math (so you can verify it yourself)

| Segment | Time | Duration |
|---|---|---|
| Hook | 0:00–0:12 | 12s |
| Why the gap exists | 0:12–0:30 | 18s |
| The idea, proven live | 0:30–0:55 | 25s |
| The payoff number | 0:55–1:00 | 5s |
| **Implementation & proof** | **1:00–2:00** | **60s** |
| Closing line | inside last few sec of above | — |
| **Total** | | **2:00** |
