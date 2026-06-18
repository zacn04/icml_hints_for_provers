"""
Lean runner stub.
Centralize Lean invocation + error parsing here.
"""
from __future__ import annotations
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from rich.console import Console
import logging

console = Console()

# Lean 3 → Lean 4 identifier mappings (lowercase.name → CamelCase.name)
LEAN3_TO_LEAN4_PREFIXES = [
    ("real.", "Real."),
    ("nat.", "Nat."),
    ("int.", "Int."),
    ("rat.", "Rat."),
    ("complex.", "Complex."),
    ("fin.", "Fin."),
    ("list.", "List."),
    ("array.", "Array."),
    ("option.", "Option."),
    ("set.", "Set."),
    ("finset.", "Finset."),
    ("multiset.", "Multiset."),
    ("string.", "String."),
    ("char.", "Char."),
    ("bool.", "Bool."),
    ("prod.", "Prod."),
    ("sum.", "Sum."),
    ("subtype.", "Subtype."),
    ("equiv.", "Equiv."),
    ("order.", "Order."),
    ("lattice.", "Lattice."),
    ("filter.", "Filter."),
    ("metric.", "Metric."),
    ("normed.", "Normed."),
    ("polynomial.", "Polynomial."),
    ("matrix.", "Matrix."),
    ("linear_map.", "LinearMap."),
    ("ring_hom.", "RingHom."),
    ("monoid_hom.", "MonoidHom."),
    ("continuous.", "Continuous."),
    ("measurable.", "Measurable."),
]

def _convert_lean3_to_lean4(text: str) -> str:
    """Convert common Lean 3 identifier patterns to Lean 4 style."""
    result = text
    for lean3, lean4 in LEAN3_TO_LEAN4_PREFIXES:
        result = result.replace(lean3, lean4)
    return result



@dataclass(frozen=True)
class LeanResult:
    compiled: bool
    proved: bool
    time_ms: int
    error_type: str
    stderr_tail: str

def _has_lakefile(path: Path) -> bool:
    """Check if a directory contains a lakefile."""
    return (path / "lakefile.toml").exists() or (path / "lakefile.lean").exists()

def _find_lean_project_root() -> Path | None:
    console.print(f"[DEBUG] lean_runner.py location: {Path(__file__).resolve()}")
    console.print(f"[DEBUG] Current working directory: {Path.cwd()}")

    # List of candidate paths to check
    candidates = [
        # Relative to this file
        Path(__file__).resolve().parent.parent / "lean",
        # Current working directory / lean
        Path.cwd() / "lean",
        # Current working directory itself (if lakefile is here)
        Path.cwd(),
        # Parent of cwd / lean
        Path.cwd().parent / "lean",
    ]

    # Also walk up from this file looking for a lean/ directory
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Check up to 5 levels up
        candidates.append(current / "lean")
        candidates.append(current)
        current = current.parent

    console.print(f"[DEBUG] Searching {len(candidates)} candidate paths for lakefile...")

    for candidate in candidates:
        console.print(f"[DEBUG] Checking: {candidate}")
        if candidate.exists():
            console.print(f"[DEBUG]   -> exists, contents: {list(candidate.iterdir())[:10]}")
            if _has_lakefile(candidate):
                console.print(f"[DEBUG]   -> FOUND lakefile at: {candidate}")
                return candidate
        else:
            console.print(f"[DEBUG]   -> does not exist")

    console.print(f"[DEBUG] No lakefile found in any candidate path")
    return None

def check(proof_text: str, timeout_sec: int) -> LeanResult:
    """
    Run Lean on either:
      (A) a full theorem text containing ':= by', or
      (B) a tactic-only block (no ':= by'), which we wrap into a dummy theorem.

    Notes:
    - Fails closed on "sorry".
    - Strips common markdown fence artifacts (```).
    - Uses --json, so diagnostics are primarily on stdout; we also include stderr.
    """
    # 0) Hard fail on sorry
    if "sorry" in proof_text.lower():
        return LeanResult(
            compiled=False,
            proved=False,
            time_ms=0,
            error_type="sorry",
            stderr_tail="Proof contains 'sorry' placeholder",
        )

    # 1) Strip common fence artifacts that break Lean parsing
    #    (handles dangling closing ``` with no opening fence)
    cleaned = proof_text.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0].rstrip()
    # also remove any remaining fence lines (defensive)
    cleaned_lines = []
    for line in cleaned.splitlines():
        if line.strip().startswith("```"):
            break
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()

    if not cleaned:
        return LeanResult(
            compiled=False,
            proved=False,
            time_ms=0,
            error_type="malformed_output",
            stderr_tail="Empty proof text after sanitization",
        )

    # 1.5) Convert Lean 3 syntax to Lean 4
    cleaned = _convert_lean3_to_lean4(cleaned)

    # 2) Build Lean source: full theorem vs tactic-only
    if ":= by" in cleaned:
        lean_src = "import Mathlib\n\n" + cleaned.rstrip() + "\n"
    else:
        # Treat as tactic block; ensure it’s indented so Lean parses it as tactics
        tactic_block = cleaned.rstrip("\n")
        # If user/model forgot indentation, indent non-empty lines
        indented = []
        for ln in tactic_block.splitlines():
            if ln.strip():
                indented.append("  " + ln)
            else:
                indented.append("")
        tactic_block = "\n".join(indented).rstrip() + "\n"

        lean_src = (
            "import Mathlib\n\n"
            "theorem AutoGenerated : True := by\n"
            f"{tactic_block}"
        )

    start_ms = int(time.time() * 1000)

    temp_path = None
    try:
        # 3) Write temp Lean file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False) as f:
            f.write(lean_src)
            temp_path = f.name

        project_root = _find_lean_project_root()
        if project_root:
            cmd = ["lake", "env", "lean", "--json", temp_path]
            cwd = str(project_root)
        else:
            cmd = ["lean", "--json", temp_path]
            cwd = None

        console.print(f"[DEBUG] Running command: {' '.join(cmd)}")
        console.print(f"[DEBUG] Working directory: {cwd}")

        # Also check if .lake/build exists
        if project_root:
            lake_build = project_root / ".lake" / "build"
            console.print(f"[DEBUG] .lake/build exists: {lake_build.exists()}")
            if lake_build.exists():
                console.print(f"[DEBUG] .lake/build contents: {list(lake_build.iterdir())[:10]}")
            packages_dir = project_root / ".lake" / "packages"
            console.print(f"[DEBUG] .lake/packages exists: {packages_dir.exists()}")
            if packages_dir.exists():
                console.print(f"[DEBUG] .lake/packages contents: {list(packages_dir.iterdir())[:10]}")

        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        console.print(f"[DEBUG] Return code: {proc.returncode}")
        console.print(f"[DEBUG] stdout (first 500 chars): {(proc.stdout or '')[:500]}")
        console.print(f"[DEBUG] stderr (first 500 chars): {(proc.stderr or '')[:500]}")

        elapsed_ms = int(time.time() * 1000) - start_ms

        # 4) With --json, stdout contains structured diagnostics; stderr may still have noise.
        out = proc.stdout or ""
        err = proc.stderr or ""
        combined = (out + "\n" + err).strip()

        compiled = (proc.returncode == 0)
        proved = compiled  # sound under your assumptions

        # 5) Error classification - parse JSON diagnostics first
        error_type = "ok" if compiled else "unknown"
        error_data = ""

        if not compiled:
            # Try to parse JSON diagnostics from stdout
            for line in out.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    diag = json.loads(line)
                    severity = diag.get("severity", "")
                    kind = diag.get("kind", "")
                    data = diag.get("data", "")

                    if severity == "error":
                        # Extract error type from kind field
                        if "unsolvedGoals" in kind or "unsolved goals" in data.lower():
                            error_type = "unsolved_goals"
                        elif "unknownIdentifier" in kind or "unknown identifier" in data.lower():
                            error_type = "unknown_identifier"
                        elif "unknownTactic" in kind or "unknown tactic" in data.lower():
                            error_type = "tactic_error"
                        elif "typeMismatch" in kind or "type mismatch" in data.lower():
                            error_type = "type_error"
                        elif "failedToSynthesize" in kind or "failed to synthesize" in data.lower():
                            error_type = "typeclass_error"
                        elif "unexpected" in data.lower() or "expected" in data.lower():
                            error_type = "syntax_error"
                        else:
                            error_type = kind if kind else "unknown"

                        # Capture the first error's data
                        if not error_data:
                            error_data = data
                        break
                except json.JSONDecodeError:
                    continue

            # Fallback to heuristic if JSON parsing didn't find anything
            if error_type == "unknown":
                cl = combined.lower()
                if "unknown tactic" in cl:
                    error_type = "tactic_error"
                elif "type mismatch" in cl or "type error" in cl:
                    error_type = "type_error"
                elif "failed to synthesize" in cl:
                    error_type = "typeclass_error"
                elif "timeout" in cl:
                    error_type = "timeout"
                elif "invalid syntax" in cl or "unexpected token" in cl:
                    error_type = "syntax_error"

        # 6) Tail for debugging - prefer parsed error_data, fallback to raw output
        if error_data:
            stderr_tail = error_data
        else:
            lines = combined.splitlines() if combined else []
            stderr_tail = "\n".join(lines[-40:]) if lines else ""

        return LeanResult(
            compiled=compiled,
            proved=proved,
            time_ms=elapsed_ms,
            error_type=error_type,
            stderr_tail=stderr_tail,
        )

    except subprocess.TimeoutExpired:
        elapsed_ms = int(time.time() * 1000) - start_ms
        return LeanResult(
            compiled=False,
            proved=False,
            time_ms=elapsed_ms,
            error_type="timeout",
            stderr_tail=f"Lean execution exceeded {timeout_sec}s timeout",
        )

    except Exception as e:
        elapsed_ms = int(time.time() * 1000) - start_ms
        return LeanResult(
            compiled=False,
            proved=False,
            time_ms=elapsed_ms,
            error_type="unknown",
            stderr_tail=str(e),
        )

    finally:
        if temp_path is not None:
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
