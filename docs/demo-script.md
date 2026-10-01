# AgentShield viva / demo script

A ~7-minute live demo. Rehearse once; keep a recorded fallback (`runs/` traces + a screen
recording) in case the model or network misbehaves on the day.

## Before the examiner arrives

```powershell
# 1. Model and data ready
ollama serve                      # in its own terminal
ollama pull qwen2.5:7b
python -m dataset.build           # splits for the benchmark

# 2. One-process demo server (API + dashboard)
cd web; npm run build; cd ..
python -m uvicorn api.main:app --host 0.0.0.0     # http://<your-ip>:8000

# 3. Publish benchmark numbers to the dashboard Results page
python -m eval.benchmark --split test --publish http://localhost:8000
```

Have two terminals and two browser tabs open (laptop + phone on the same Wi-Fi, pointing at
`http://<your-ip>:8000`). Confirm the connection badge reads **connected**.

## The script

1. **Show the unprotected agent being manipulated.** Run the "before" case with no defense:
   ```powershell
   python -m eval.run injections --scenarios data/attacks/before_demo.json --defense none --verbose --only <id>
   ```
   Point out the trace: the agent reads injected content and emails the fake secret out. Show
   the outbox / `leaked_secrets` in the report.

2. **Turn on AgentShield and repeat.** Same scenario, `--defense full`:
   ```powershell
   python -m eval.run injections --scenarios data/attacks/before_demo.json --defense full --verbose --only <id>
   ```
   The send is **BLOCKED**; the outbox is empty. Read the firewall reason aloud.

3. **Incident replay.** On the dashboard → **Incidents**, open that run and step through it: the
   provenance tags (EXTERNAL / PRIVATE), the flagged content, and the per-layer scores.

4. **A Hindi or Tamil attack being caught.** In **Playground**, paste a Hindi or Tamil injection
   (or Hinglish) and scan it. Show the verdict, the risk bar, and the highlighted chunk — the
   multilingual rule/classifier layer fires where an English-only filter would not.

5. **A canary catching what detectors missed.** Use the benign-looking exfil case: the injected
   page has no trigger words, so the detectors do not flag it, but the **canary/taint** layer
   blocks the outgoing email and traces it to `private/…` and the external page. This is the core
   contribution — emphasize that detection alone would have failed here.

6. **Open it on your phone.** Show the same dashboard live on the phone: bottom tab bar, a toast
   popping up for the blocked attack, stat cards and the event feed updating in real time without
   a refresh.

7. **Let the examiner try the Playground.** Hand them the phone or laptop; have them paste any
   text (any language, with hidden HTML or base64 if they like) and watch it get scored live.

8. **End on the numbers.** Dashboard → **Results**: the attack-success / detection / false-
   positive table, the ablation chart (removing each layer), and per-language detection. Close by
   restating the two findings: multilingual coverage, and provenance catching what detection
   misses.

## If something fails

- Model slow/unreachable: switch to **replay** — open a saved incident in the dashboard and walk
  through steps 3–8 using pre-recorded data and the published Results.
- Dashboard not updating: the connection badge shows the WebSocket state; it auto-reconnects.
  Reload the tab if needed; history reloads from the API.
