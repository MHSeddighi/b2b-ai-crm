"""Action engine: definitions + eligibility + ranking + next-best-action."""
from backend.crm.actions.definitions import ACTIONS, get_meta
from backend.crm.actions.eligibility import is_eligible
from backend.crm.actions.next_best_action import recommend
from backend.crm.actions.ranking import compute_priority

__all__ = ["ACTIONS", "get_meta", "is_eligible", "recommend", "compute_priority"]
