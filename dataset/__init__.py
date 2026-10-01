"""Dataset tooling for AgentShield.

Code lives here; the data artifacts live under ``data/``. The pipeline unifies three
attack sources (public corpora, human-authored multilingual samples, and seed examples)
with an authored benign set, then deduplicates and splits them for training and testing.
"""
