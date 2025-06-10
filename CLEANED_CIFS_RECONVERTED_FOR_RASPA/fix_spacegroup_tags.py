
#!/usr/bin/env python3
"""fix_spacegroup_tags.py  ·  make CIF space‑group headers RASPA‑friendly

Changes applied
---------------
• _space_group_name_H-M_alt          → _symmetry_space_group_name_H-M
• _space_group_IT_number             → _symmetry_Int_Tables_number
• _space_group_symop_operation_xyz   → _symmetry_equiv_pos_as_xyz
• guarantees the space‑group string is single‑quoted
• removes *all* spaces inside symmetry‑operation strings
  e.g.  'x, y, z'  →  'x,y,z'
• works no matter how the CIF is indented
"""

import argparse, pathlib, re, shutil, sys
from typing import Iterable

# ---------- patterns -----------------------------------------------------

TAG_MAP = {
    r"^(?P<ws>\s*)_space_group_name_H-M_alt\b":
        "{ws}_symmetry_space_group_name_H-M",
    r"^(?P<ws>\s*)_space_group_IT_number\b":
        "{ws}_symmetry_Int_Tables_number",
    r"^(?P<ws>\s*)_space_group_symop_operation_xyz\b":
        "{ws}_symmetry_equiv_pos_as_xyz",
}

SG_TAG = "_symmetry_space_group_name_H-M"
SG_RE  = re.compile(rf"^(?P<ws>\s*){SG_TAG}\s+(?P<val>.+)$", re.I)
QUOTED = re.compile(r"^['\"](.+?)['\"]$")

# quoted symmetry operation – remove blanks
QUOTED_OP_RE = re.compile(r"'(.*?)'")  # non‑greedy

def _replace_aliases(line: str) -> str:
    for pattern, repl in TAG_MAP.items():
        m = re.match(pattern, line)
        if m:
            return re.sub(pattern, repl.format(ws=m['ws']), line)
    return line

def _fix_space_group(line: str) -> str:
    if (m := SG_RE.match(line)):
        val = m['val'].strip()
        if (q := QUOTED.match(val)):
            val = q.group(1)           # remove existing quotes
        return f"{m['ws']}{SG_TAG}    '{val}'\n"
    return line

def _compress_ops(line: str) -> str:
    # remove spaces inside EVERY single‑quoted string
    def compact(match):
        return "'" + match.group(1).replace(" ", "") + "'"
    return re.sub(r"'([^']*)'", compact, line)
# -------------------------------------------------------------------------

def fix_lines(lines: Iterable[str]) -> Iterable[str]:
    in_symm_loop = False
    for raw in lines:
        line = _replace_aliases(raw)
        line = _fix_space_group(line)

        # track whether we're inside the symmetry‑operation loop
        if line.lstrip().startswith("loop_"):
            in_symm_loop = False  # reset; next tags will set it
        if "_symmetry_equiv_pos_as_xyz" in line:
            in_symm_loop = True
            yield line
            continue

        if in_symm_loop:
            # compress only if we are still in that loop
            if line.lstrip().startswith("_") or line.lstrip().startswith("loop_") or not line.strip():
                in_symm_loop = False
            else:
                line = _compress_ops(line)

        yield line

# -------------------------------------------------------------------------

def process_file(path: pathlib.Path, *, inplace: bool, backup_ext: str):
    original = path.read_text(errors="replace").splitlines(keepends=True)
    fixed    = list(fix_lines(original))

    if fixed == original:
        print(f"✓ {path}: already OK")
        return

    if inplace:
        if backup_ext:
            shutil.copy2(path, path.with_suffix(path.suffix + backup_ext))
        path.write_text("".join(fixed))
        print(f"★ {path}: patched in place")
    else:
        out = path.with_name(path.stem + "_fixed" + path.suffix)
        out.write_text("".join(fixed))
        print(f"★ {path.name} → {out.name}")

# -------------------------------------------------------------------------

def collect(root: pathlib.Path, recursive: bool):
    if root.is_file():
        return [root] if root.suffix.lower() == ".cif" else []
    pattern = "**/*.cif" if recursive else "*.cif"
    return sorted(root.rglob('*.cif') if recursive else root.glob('*.cif'))

# -------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fix CIF space‑group tags for RASPA.")
    ap.add_argument("path", type=pathlib.Path,
                    help="single CIF file or directory")
    ap.add_argument("--recursive", action="store_true",
                    help="process sub‑directories recursively")
    ap.add_argument("--in-place", action="store_true",
                    help="modify files in place instead of writing *_fixed.cif")
    ap.add_argument("--backup", default="", metavar=".ext",
                    help="backup suffix when using --in-place (e.g. .bak)")
    args = ap.parse_args(argv)

    files = collect(args.path, args.recursive)
    if not files:
        print("No CIF files found.", file=sys.stderr)
        sys.exit(1)

    for cif in files:
        process_file(cif, inplace=args.in_place, backup_ext=args.backup)

if __name__ == "__main__":
    main()
