# TRIPWIRE — 3-Minute Live Demo Script

**Format:** screen-recording of the live website (plus one 30-second cut
to the AWS Console), you talking over it — no slides. Q&A style
throughout (ask, then answer). Total runtime: **3:00 exactly**, split
as:

| Segment | Time | Duration |
|---|---|---|
| **Problem statement + live demo** | **0:00–1:00** | **60s (required)** |
| **Implementation & tech stack** | **1:00–2:30** | **90s (required)** |
| **AWS deployment proof** | **2:30–3:00** | **30s (required)** |

Read the **[SAY]** lines out loud, close to word for word. The **[DO]**
lines are exactly what to click/open at that moment — rehearse the
clicks so your hands are ahead of your mouth.

---

## 0:00 – 1:00 — Problem statement + live demo (60 sec — required)

**[DO]** Site's landing section is open. Just the screen, or your face
in a corner — don't scroll yet.

**[SAY]**
> "Quick question — how much do you think India loses every year to
> electricity theft? ₹1.32 lakh crore. And the gap between the
> best-performing utility at catching it and the worst? Forty-five
> percentage points.
>
> Why such a gap? Not because small utilities are worse at their job —
> they simply haven't seen enough real theft cases to learn the
> pattern. The obvious fix is to share data across utilities. Except
> raw meter data reveals private homes, habits, businesses — utilities
> legally can't share that. So what do you actually do?"

**[DO]** Scroll to "See it work." Point at "The boundary, live" panel.

**[SAY]**
> "You don't share the data — you share the *shape* of the pattern, and
> a real policy engine enforces that boundary, not a promise. Watch: a
> raw reading — denied, automatically. A signature with one identity
> field left on by a bug — still denied, and it names the exact leak.
> Only a properly stripped signature — allowed."

**[DO]** Point at "The pool, live" panel, Site C row.

**[SAY]**
> "And here's the payoff: Site C, a small, low-data utility, alone
> catches a third of its theft. Once it checks against what other sites
> found — without ever seeing their data — that jumps to two-thirds."

---

## 1:00 – 2:30 — Implementation & tech stack (90 sec — required)

This is the half that separates you from a team that showed a slide
with a number on it. Slow down slightly here — it's dense.

**[SAY]**
> "Now let's talk implementation — why this isn't just a nice-looking
> demo.
>
> The frontend is React and TypeScript, built with Vite. The backend is
> Python, served through FastAPI, running real machine-learning code —
> a scikit-learn Isolation Forest doing the actual anomaly detection —
> alongside a real Cedar policy engine, the same authorization language
> AWS itself uses internally, deciding every single allow or deny. The
> two talk over live server-sent events, so this page isn't polling for
> updates — it's streaming them, live."

**[DO]** Click **"Run TRIPWIRE now"** on camera. Point at the seed
number that changes next to the pool size.

**[SAY]**
> "Watch this number — it just changed. Every click regenerates a
> brand-new random dataset, a new seed, shown right here, so nobody can
> accuse us of quietly cherry-picking one lucky run."

**[DO]** Scroll to "Pipeline, stage by stage."

**[SAY]**
> "This pipeline diagram isn't a canned animation either — each stage
> lights up the instant that real backend function actually finishes
> for that site: detect, abstract, check the Cedar gate, then the
> pooled recheck."

**[DO]** Scroll to "Validation across seeds."

**[SAY]**
> "This panel reruns the *entire* pipeline eight independent times,
> with eight different seeds, and proves the improvement holds every
> time — and that pooling never once made false positives worse."

**[DO]** Scroll to "Decision log, this session."

**[SAY]**
> "And this decision log is a real audit trail — every allow, every
> deny, timestamped, with the reason — exactly what a compliance
> officer at a utility would actually want to inspect. All of it running
> behind Nginx and a systemd service, so it stays up and restarts itself
> if it ever crashes."

---

## 2:30 – 3:00 — AWS deployment proof (30 sec — required)

**What to have open before you hit record:** two browser tabs, both
already logged in / loaded so there's zero waiting on screen —
**Tab 1**: the live site. **Tab 2**: AWS Console → EC2 → **Instances**
page, with your `tripwire-server` instance visible in the list
(state: Running). Practice the tab-switch (Ctrl+Tab or click) once
before recording so it's instant.

**[DO]** Switch to **Tab 2** (AWS Console, EC2 → Instances).

**[SAY]**
> "And this isn't running on my laptop for this recording. This is the
> actual AWS EC2 Console — the instance is called `tripwire-server`,
> state: Running, on AWS's free tier."

**[DO]** Click the instance to open its details panel. Point at (or
briefly click into) the **"Networking"** tab to show the **Public IPv4
address / Public IPv4 DNS** field.

**[SAY]**
> "Here's its public address."

**[DO]** Switch back to **Tab 1** (the live site) and point at the
browser's address bar, showing the same address.

**[SAY]**
> "Same address as the site you just watched. Same machine, live, right
> now, reachable by anyone. Share the pattern — never the person.
> That's TRIPWIRE."

---

## Before you hit record — checklist

- [ ] Open and pre-load both tabs (live site + AWS Console → EC2 →
      Instances) before recording so there's no loading delay.
- [ ] Refresh the live site once so seed/pool numbers aren't stale from
      earlier testing.
- [ ] Click "Reset log" on the decision log so it's not cluttered from
      rehearsals.
- [ ] Close other tabs/notifications, full-screen the browser.
- [ ] Do one silent run-through of every click first, then one full
      run-through out loud with a stopwatch, before the real take.
- [ ] Confirm your internet is stable — the swarm run and validation
      panel both hit the live backend; lag mid-recording eats your time.
- [ ] Speak slightly slower than feels natural, especially through the
      implementation section — it's the densest 90 seconds.
