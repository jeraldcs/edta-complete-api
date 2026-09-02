"""Remove Cursor co-author trailer from git commit messages (stdin -> stdout)."""
import sys

MARKER = "Co-authored-by: Cursor <cursoragent@cursor.com>"
text = sys.stdin.read()
lines = [line for line in text.splitlines() if line.strip() != MARKER]
sys.stdout.write("\n".join(lines))
if text.endswith("\n"):
    sys.stdout.write("\n")
