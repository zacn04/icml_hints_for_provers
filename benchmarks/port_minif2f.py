import json
import re
from pathlib import Path

MINIF2F_FILE = Path("benchmarks/test.lean")
IMPORT_FILE  = Path("benchmarks/minif2f_import.lean")
OUT_FILE     = Path("benchmarks/minif2f.jsonl")

BEGIN_RE = re.compile(r"\bbegin\b")
END_RE   = re.compile(r"\bend\b")

def is_import_line(line: str) -> bool:
    return line.strip().startswith("import ")

def main():
    text = MINIF2F_FILE.read_text(encoding="utf-8")
    import_text = IMPORT_FILE.read_text(encoding="utf-8").strip()

    lines = text.splitlines()
    n = len(lines)

    # 1) Skip non-Lean header junk until first import
    i = 0
    while i < n and not is_import_line(lines[i]):
        i += 1
    if i == n:
        raise RuntimeError("No import statements found in MiniF2F file")

    # 2) Global context = from first import up to first theorem
    context_lines = []
    while i < n and not lines[i].startswith("theorem "):
        context_lines.append(lines[i])
        i += 1

    file_context = "\n".join(context_lines).strip()
    full_context = import_text + "\n\n" + file_context

    rows = []

    while i < n:
        if not lines[i].startswith("theorem "):
            i += 1
            continue

        # 3) Parse theorem header until we see ':='
        header_lines = [lines[i]]
        name = lines[i].split()[1]
        i += 1

        while i < n and ":=" not in lines[i]:
            header_lines.append(lines[i])
            i += 1
        if i >= n:
            break

        header_lines.append(lines[i])  # line containing ':='
        header = "\n".join(header_lines).strip()

        goal = ""

        # Determine proof style from the ':=' line remainder
        decl_line = lines[i]
        after_decl = decl_line.split(":=", 1)[1].strip()  # text after ':=' on same line
        i += 1

        # 4) Skip proof
        # Case A: ":= begin ... end" (begin may be on same line or next line)
        # Case B: ":= by ..." (no begin/end block necessarily) -> do NOT stack-skip
        # Case C: ":= by" then proof on following lines -> still no begin/end required
        if BEGIN_RE.search(after_decl) or (i < n and lines[i].strip() == "begin"):
            # If begin isn't on the same line, consume the 'begin' line
            if i < n and lines[i].strip() == "begin":
                depth = 1
                i += 1
            else:
                # begin token was on the ':=' line
                depth = 1

            # Stack-scan until depth returns to 0
            while i < n and depth > 0:
                line = lines[i]
                # Count tokens, not exact line matches (handles `end,` etc.)
                depth += len(BEGIN_RE.findall(line))
                depth -= len(END_RE.findall(line))
                i += 1
        else:
            # Proof is `by ...` or term-style; we don't need to skip anything here.
            # The next theorem starts at a later "theorem " line, and our outer loop will find it.
            pass

        # 5) Emit stripped theorem statement
        stripped_theorem = header.rsplit(":=", 1)[0].rstrip() + " := by"
        rows.append({
            "id": name,
            "theorem": stripped_theorem,
            "context": full_context,
            "goal": goal,
        })

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"[ok] Extracted {len(rows)} theorems → {OUT_FILE}")

if __name__ == "__main__":
    main()
