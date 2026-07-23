#!/bin/bash
# Run cases from cases.csv.
#
#   scripts/run.sh                       # every case, sequentially
#   scripts/run.sh medium_sand low_silt  # named cases
#   scripts/run.sh --jobs 4              # four cases at a time (10 cores here)
#   scripts/run.sh --exodus medium_sand  # also write the ParaView field file
#   scripts/run.sh --keep-raw ...        # do not delete the raw CSVs after archiving
#
# Each case runs the single input inputs/cycle.i with its permeability applied
# as a command-line override, writes raw sampler CSVs into results/<case>/, folds
# them into data/<case>.npz (~2.6 MB), then deletes the raw CSVs.
#
# Cost per case: ~4 min, ~20 MB transient, 2.6 MB kept. With --exodus, add ~18 MB
# kept. The sweep is embarrassingly parallel -- each case is an independent
# serial solve -- so --jobs N gives close to N-fold speedup until you run out of
# cores or memory (~125 MB per case).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

JOBS=1
EXODUS=false
KEEP_RAW=false
CASES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --jobs|-j)   JOBS="$2"; shift 2 ;;
    --exodus)    EXODUS=true; shift ;;
    --keep-raw)  KEEP_RAW=true; shift ;;
    --list)      awk -F, 'NR>1 && $1!="" {printf "  %-22s %s\n", $1, $7}' cases.csv; exit 0 ;;
    -h|--help)   sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)          echo "unknown flag: $1" >&2; exit 1 ;;
    *)           CASES+=("$1"); shift ;;
  esac
done

# shellcheck disable=SC1091
source "$REPO/scripts/env.sh"

if [ ! -x "$REPO/borehole1-opt" ]; then
  echo "error: borehole1-opt not built. Run: source scripts/env.sh && make -j8" >&2
  exit 1
fi

# Pull one case's parameters out of cases.csv. The permeability field contains
# commas? No -- it is space separated -- but it does contain runs of spaces, so
# read the CSV with python rather than cut.
read_case() {
  "$MOOSE_PYTHON" - "$1" <<'PY'
import csv, sys
want = sys.argv[1]
with open("cases.csv") as fh:
    for row in csv.DictReader(fh):
        if row["case"] == want:
            print("\t".join([row["permeability"], row["dt"], row["nl_abs_tol"],
                             row["nl_max_its"], row["archive_stride"]]))
            break
    else:
        sys.exit(1)
PY
}

if [ "${#CASES[@]}" -eq 0 ]; then
  while IFS= read -r c; do CASES+=("$c"); done < <("$MOOSE_PYTHON" -c "
import csv
print('\n'.join(r['case'] for r in csv.DictReader(open('cases.csv')) if r['case']))")
fi

run_one() {
  local case="$1"
  local params; params=$(read_case "$case") || { echo "!! unknown case: $case" >&2; return 1; }
  local perm dt tol its stride
  IFS=$'\t' read -r perm dt tol its stride <<<"$params"

  echo "=== $case  (dt=$dt, k=$perm) started $(date '+%H:%M:%S')"
  local t0=$SECONDS
  ./borehole1-opt -i inputs/cycle.i \
      Materials/perm/permeability="$perm" \
      Executioner/dt="$dt" \
      Executioner/nl_abs_tol="$tol" \
      Executioner/nl_max_its="$its" \
      Outputs/file_base="results/$case/output" \
      Outputs/exodus/enable="$EXODUS" \
      > "results/$case.log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "!! $case FAILED (exit $rc) — see results/$case.log" >&2
    return $rc
  fi

  "$MOOSE_PYTHON" scripts/archive.py "$case" --stride "$stride" \
      $([ "$KEEP_RAW" = true ] && echo --keep-raw) || return 1

  echo "=== $case done in $((SECONDS - t0))s"
}

mkdir -p results data

failed=()
if [ "$JOBS" -gt 1 ]; then
  echo "running ${#CASES[@]} case(s), $JOBS at a time"
  pids=()
  for c in "${CASES[@]}"; do
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n 2>/dev/null || sleep 1; done
    run_one "$c" &
    pids+=("$!:$c")
  done
  for pc in "${pids[@]}"; do
    wait "${pc%%:*}" || failed+=("${pc##*:}")
  done
else
  for c in "${CASES[@]}"; do run_one "$c" || failed+=("$c"); done
fi

if [ "${#failed[@]}" -gt 0 ]; then
  echo "failed: ${failed[*]}" >&2
  exit 1
fi
echo "all cases complete — archives in data/, regenerate figures with scripts/figures.sh"
