"""Deterministic Customer Intelligence layer.

Signal -> State -> Action, all computed in Python/SQL (never by the LLM).

The chatbot consumes these results through dedicated tools; it may only
explain/personalize them, never invent a signal, score, threshold, or action.
"""
