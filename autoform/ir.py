"""
IR definition + perturbations.
Small, deterministic, Lean-aware.
"""
from __future__ import annotations
import enum
import random
from dataclasses import dataclass
from typing import Tuple, List, Optional


class PerturbMode(enum.Enum):
    SKELETON = "skeleton"
    PARAPHRASE = "paraphrase"
    COMMENT = "comment"
    GOAL_HINT_ONLY = "goal_hint"  # NL tactic-suggestion comment, empty tactic prefix


@dataclass(frozen=True)
class IR:
    theorem: str
    tactic_prefix: Tuple[str, ...]
    goal_hint: Optional[str]
    instruction: Optional[str] = None
    comment_prefix: Optional[str] = None

TACTIC_SKELETONS = [
    (),
    ("simp",),
    ("intro",),
    ("intros",),
    ("constructor",),
    ("refine ?_",),
    ("refine ⟨?_, ?_⟩",),
    ("aesop",),
    ("norm_num",),
    ("linarith",),
    ("nlinarith",),
    ("ring",),
    ("ring_nf",),
    ("simp", "try aesop"),
    ("simp", "try nlinarith"),
]


GOAL_HINTS = [
    None,
    "Start by simplifying the goal and hypotheses using `simp`.",
    "If the goal is an implication or forall, introduce variables.",
    "If the goal is a conjunction or existence, build it using `constructor` or `refine`.",
    "If arithmetic is involved, try `norm_num`, then `linarith` or `nlinarith`.",
    "If the goal looks routine, try `aesop` after simplification.",
    "If the proof requires rewriting, look for a lemma in the context and rewrite.",
    "If the goal involves recursion on naturals, consider induction.",
]


INSTRUCTION_PARAPHRASES = [
    "Prove the following theorem in Lean 4:",
    "Complete this Lean 4 proof:",
    "Find a formal proof for the following:",
    "Show that the following statement holds:",
    "Write a tactic proof for this theorem:",
    "Construct a formal proof of the following:",
    "Provide a Lean 4 proof for:",
    "Demonstrate the following result formally:",
    "Give a complete tactic proof:",
    "Prove this result using Lean 4 tactics:",
    "Formalize a proof of the following theorem:",
    "Establish the following in Lean 4:",
    "Derive a proof for the following statement:",
    "Supply a formal tactic proof for:",
    "Verify the following theorem in Lean 4:",
    "Prove the following:",
]


COMMENT_PREFIXES = [
    "/- approach alpha -/",
    "/- strategy beta -/",
    "/- method gamma -/",
    "/- path delta -/",
    "/- route epsilon -/",
    "/- attempt zeta -/",
    "/- angle eta -/",
    "/- direction theta -/",
    "/- variant iota -/",
    "/- form kappa -/",
    "/- mode lambda -/",
    "/- plan mu -/",
    "/- way nu -/",
    "/- style xi -/",
    "/- view omicron -/",
    "/- take pi -/",
]


def make_base_ir(theorem: str, context: str) -> IR:
    return IR(
        theorem=theorem.strip(),
        tactic_prefix=(),
        goal_hint=None,
    )


def perturb(
    base: IR,
    seed: int,
    k: int,
    mode: PerturbMode = PerturbMode.SKELETON,
) -> List[IR]:
    """
    Generate k deterministic IR variants.
    This defines the proof search space.
    """
    variants: List[IR] = []

    for i in range(k):
        if mode == PerturbMode.SKELETON:
            tactic = TACTIC_SKELETONS[i % len(TACTIC_SKELETONS)]
            hint = GOAL_HINTS[(i // len(TACTIC_SKELETONS)) % len(GOAL_HINTS)]
            ir = IR(
                theorem=base.theorem,
                tactic_prefix=tactic,
                goal_hint=hint,
            )

        elif mode == PerturbMode.PARAPHRASE:
            instruction = INSTRUCTION_PARAPHRASES[i % len(INSTRUCTION_PARAPHRASES)]
            ir = IR(
                theorem=base.theorem,
                tactic_prefix=(),
                goal_hint=None,
                instruction=instruction,
            )

        elif mode == PerturbMode.COMMENT:
            comment = COMMENT_PREFIXES[i % len(COMMENT_PREFIXES)]
            ir = IR(
                theorem=base.theorem,
                tactic_prefix=(),
                goal_hint=None,
                comment_prefix=comment,
            )

        elif mode == PerturbMode.GOAL_HINT_ONLY:
            # Cycle through the 7 NON-EMPTY goal-hint comments with empty tactic prefix.
            # Skip GOAL_HINTS[0] (None) so every attempt has a real hint comment.
            non_empty = [h for h in GOAL_HINTS if h is not None]
            hint = non_empty[i % len(non_empty)]
            ir = IR(
                theorem=base.theorem,
                tactic_prefix=(),
                goal_hint=hint,
            )

        variants.append(ir)

    return variants
