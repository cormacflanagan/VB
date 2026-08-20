#!/bin/sh
# Rebuild every report from the current rosters. Run from the repo root.
#
#   scripts/rebuild.sh
#
# Order matters: collect fetches the twelve-month competition record for each group and
# writes the snapshots the renderers read, so nothing downstream can run until it has.
# Head-to-head is a separate fetch (match feed rather than tournament list) and is only
# refreshed for the groups whose pages show a crosstable.
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
GROUPS="18U 17U 2027 2028 2028_top20 2028_top30 2027_younger 2028_younger"

cd "$ROOT/data"
export PYTHONPATH="$ROOT/scripts"

echo "=== collect"
python3 "$ROOT/scripts/collect_group.py" $GROUPS

echo "=== head-to-head"
python3 "$ROOT/scripts/h2h.py" $GROUPS

echo "=== calendar"
python3 "$ROOT/scripts/calendar.py" 2027

echo "=== render"
python3 "$ROOT/scripts/render_group.py" $GROUPS
python3 "$ROOT/scripts/calendar_page.py" 2027
for g in 2028_top30 2027_younger 2028_younger; do
  python3 "$ROOT/scripts/partners_page.py" "$g"
done

mv -f ./*.html "$ROOT/docs/"
echo "=== done"
ls -la "$ROOT/docs/"
