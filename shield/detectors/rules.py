"""Layer 1: a fast multilingual rule filter.

Precompiled patterns plus structural signals from the preprocessing metadata. It is built
for recall and speed (well under 5 ms), and it accepts some false positives that the later,
costlier layers are there to clean up.
"""

from __future__ import annotations

import re

from shield.detectors.base import Context, Signal, timed
from shield.preprocess.types import Chunk

# (compiled pattern, weight, reason). Patterns are matched case-insensitively against the
# de-obfuscated text. These are detection signatures, not functional payloads.
_TRIGGERS: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier|preceding)\s+(instruction|message|prompt|command|direction|rule)", re.I), 0.6, "ignore-previous"),
    (re.compile(r"disregard\s+(all\s+|any\s+)?(the\s+|your\s+)?(previous|prior|above|earlier|system)", re.I), 0.6, "disregard-previous"),
    (re.compile(r"forget\s+(everything|all|your|the\s+(previous|prior|above))", re.I), 0.5, "forget-previous"),
    (re.compile(r"\b(you\s+are\s+now|from\s+now\s+on\s+you|act\s+as|pretend\s+to\s+be|you\s+must\s+now)\b", re.I), 0.45, "role-reassignment"),
    (re.compile(r"\b(system\s+prompt|developer\s+message|new\s+instructions?|updated\s+instructions?)\b", re.I), 0.4, "meta-instruction"),
    (re.compile(r"\b(do\s+not|don't|never)\s+(tell|inform|notify|alert|mention\s+to)\s+(the\s+)?(user|owner|human)\b", re.I), 0.5, "hide-from-user"),
    (re.compile(r"\b(reveal|print|output|disclose|show|send)\s+(me\s+)?(the\s+)?(system\s+prompt|password|api\s*key|secret|credential)", re.I), 0.6, "exfiltration-request"),
    (re.compile(r"\b(i\s+am|as)\s+(the\s+)?(administrator|admin|developer|system|owner)\b", re.I), 0.35, "authority-claim"),
    # Hindi (Devanagari)
    (re.compile(r"(पिछले|पिछली|पूर्व)\s*(निर्देश|आदेश|संदेश)"), 0.6, "ignore-previous-hi"),
    (re.compile(r"(निर्देश(ों)?|आदेश(ों)?)\s*को\s*(अनदेखा|नज़रअंदाज़|अनदेखी)"), 0.6, "ignore-hi"),
    (re.compile(r"सिस्टम\s*(प्रॉम्प्ट|प्रॉम्ट)"), 0.4, "system-prompt-hi"),
    # Hinglish (romanized)
    (re.compile(r"\b(pichle|purane|upar\s+ke)\s+(instruction|nirdesh|message)", re.I), 0.5, "ignore-previous-hinglish"),
    (re.compile(r"\b(ignore|bhul\s*jao|nazarandaz)\s+(karo|kar\s+do|kardo)\b", re.I), 0.5, "ignore-hinglish"),
    # Tamil
    (re.compile(r"(முந்தைய|முன்பு)\s*(வழிமுறை|அறிவுறுத்தல்|கட்டளை)"), 0.6, "ignore-previous-ta"),
    (re.compile(r"புறக்கணி"), 0.45, "ignore-ta"),
    # Tanglish
    (re.compile(r"\b(ignore|marandhuru)\s+(pannu|pannunga|panniru)\b", re.I), 0.5, "ignore-tanglish"),
]

# Mock-tool and capability names that should not appear inside untrusted data.
_TOOLS = re.compile(r"\b(send_email|http_post|read_file|write_file|browse_web|transfer_money|list_emails)\b", re.I)
# An assistant/agent being addressed and told to act.
_ADDRESS = re.compile(r"\b(assistant|a\.?i\.?|agent|chatbot|language\s+model|llm|the\s+bot|the\s+model)\b", re.I)
_IMPERATIVE = re.compile(r"\b(must|should|now|immediately|please|do|send|email|forward|post|execute|run|fetch|delete|ignore|reveal|print|output)\b", re.I)
# A secret-shaped string sitting next to a URL (an exfiltration setup).
_SECRET_NEAR_URL = re.compile(r"(sk-[A-Za-z0-9_-]{6,}|[A-Z0-9]{12,}|(?:IBAN|iban)[-\s][A-Z0-9-]{6,}).{0,60}https?://|https?://.{0,60}(sk-[A-Za-z0-9_-]{6,}|[A-Z0-9]{12,})", re.S)


class RuleDetector:
    name = "rules"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def _evaluate(self, chunk: Chunk) -> tuple[float, list[str]]:
        haystack = "\n".join([chunk.text, *chunk.decoded])
        score = 0.0
        reasons: list[str] = []

        for pattern, weight, reason in _TRIGGERS:
            if pattern.search(haystack):
                score += weight
                reasons.append(reason)

        if _ADDRESS.search(haystack) and _IMPERATIVE.search(haystack):
            score += 0.3
            reasons.append("imperative aimed at the assistant")
        if _TOOLS.search(haystack):
            score += 0.3
            reasons.append("tool name inside data")
        if _SECRET_NEAR_URL.search(haystack):
            score += 0.3
            reasons.append("secret-shaped string near a URL")

        # Obfuscation is itself a signal: benign content rarely hides or encodes text.
        if chunk.hidden:
            score += 0.25
            reasons.append("hidden from reader")
        if chunk.encoded:
            score += 0.2
            reasons.append("encoded payload")
        if chunk.homoglyph:
            score += 0.2
            reasons.append("look-alike letters")
        if chunk.invisible:
            score += 0.15
            reasons.append("invisible characters")

        return score, reasons

    def score(self, chunk: Chunk, context: Context) -> Signal:
        def run() -> Signal:
            raw, reasons = self._evaluate(chunk)
            reason = ", ".join(reasons[:3]) if reasons else "no rule matched"
            return Signal.from_score(min(raw, 1.0), reason, layer="L1", threshold=self.threshold, evidence=reasons)

        return timed(run)
