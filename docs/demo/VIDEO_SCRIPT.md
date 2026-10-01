# AgentShield demo video script (3–5 minutes)

A tight, repeatable recording. Use **scripted demo mode** so the sequence is identical every
take: start the API with `DEMO_MODE=true` (it seeds the same incident each boot), and use the
saved scenario file for the live attack. Record at 1080p; keep the dashboard in dark mode.

**Setup before recording**
```powershell
ollama serve ; ollama pull qwen2.5:1.5b        # small model is fine for the video
cd web ; npm run build ; cd ..
$env:DEMO_MODE="true"; python -m uvicorn api.main:app --host 0.0.0.0   # http://localhost:8000
```
Open two things: the dashboard (`http://localhost:8000`) and a terminal.

---

## 0:00 – 0:30 — Problem (narration over title slide)
> "LLM agents read web pages, emails, and files, then take actions — send mail, call APIs. If an
> attacker hides instructions in that content, the agent can be hijacked. This is *indirect
> prompt injection*. Today's defenses are English-only and rarely tested against a smart attacker.
> AgentShield is a layered, provenance-aware defense that fixes both."

## 0:30 – 1:10 — Unprotected agent is manipulated
- **Click:** terminal. Run:
  ```powershell
  python -m eval.run injections --scenarios data/attacks/before_demo.json --defense none --verbose --only I01
  ```
- **Narrate** while the trace scrolls:
> "No defense. The agent reads a review page that hides an instruction, then emails a secret to
> the attacker. Look — the outbox shows the leaked key. The agent was fully hijacked."

## 1:10 – 1:55 — Same attack, stopped by AgentShield
- **Click:** run again with `--defense full`:
  ```powershell
  python -m eval.run injections --scenarios data/attacks/before_demo.json --defense full --verbose --only I01
  ```
- **Narrate:**
> "Now with AgentShield. Same attack. The send is BLOCKED — reason: canary leak from the
> credentials file, triggered by the external page. The outbox is empty. The task still works."

## 1:55 – 2:35 — Incident replay on the dashboard
- **Click:** dashboard → **Incidents** → open the seeded incident.
- **Narrate**, pointing:
> "Every step is inspectable. Here's the provenance — EXTERNAL content, PRIVATE data — the
> per-layer scores, and the firewall's decision with its reason."

## 2:35 – 3:05 — Multilingual + canary (the two contributions)
- **Click:** **Playground**. Paste a Hindi/Hinglish injection. Scan.
> "A Hindi attack — caught by the multilingual detector, where an English-only filter would miss
> it."
- **Point back to the blocked send:**
> "And the canary caught an exfiltration the text detectors missed — because the page had no
> trigger words. Detection alone would have failed; provenance saved it."

## 3:05 – 3:35 — Live on a phone
- **Show phone** (same Wi-Fi, `http://<ip>:8000`): bottom tab bar, a toast firing on the block,
  stat cards updating.
> "It's a real-time app — works on a phone, updates live over WebSockets, no refresh."

## 3:35 – 4:10 — Results
- **Click:** **Results**.
> "The numbers: attack-success down from [RESULT] to [RESULT], utility held, false positives low,
> and an ablation showing each layer's contribution. Full results are from the local system; the
> hosted demo runs a small model."

## 4:10 – 4:30 — Close
> "AgentShield: multilingual detection plus provenance-based canary and taint tracking, catching
> what detection misses. Code, dataset, and paper are linked below. Thanks for watching."

---

**Fallback:** if the model is slow, use the seeded demo incident (already in the dashboard under
Incidents) and the published Results page — the whole walk-through works without a live agent run.
