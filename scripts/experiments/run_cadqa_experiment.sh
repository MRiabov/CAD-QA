#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RTK=()
if command -v rtk >/dev/null 2>&1; then
  RTK=(rtk)
fi

run_cmd() {
  printf '+'
  printf ' %q' "${RTK[@]}" "$@"
  printf '\n'
  "${RTK[@]}" "$@"
}

run_python() {
  run_cmd uv run python "$@"
}

run_suite() {
  run_python -m scripts.experiments.run_experiment_suite "$@"
}

usage() {
  cat <<'EOF'
Usage: scripts/experiments/run_cadqa_experiment.sh <command> [args]

Commands:
  preflight              Compile, test, list/dry-run smoke, and dry-run SFT canary
  list [manifest]        List runs in a manifest
  smoke [extra args]     Run configs/orchestration_smoke.yaml with --resume
  smoke-dry-run          Dry-run configs/orchestration_smoke.yaml
  canary-dry-run         Dry-run answer_sft_canary with dependencies
  canary [extra args]    Run answer_sft_canary with dependencies
  monitor [runs_dir]     Print run_status.json summaries
  run <manifest> [args]  Pass through to scripts.experiments.run_experiment_suite

The script prefixes commands with rtk when available, and runs directly when
rtk is absent on a bootstrapped remote instance.
EOF
}

command_name="${1:-preflight}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "$command_name" in
  preflight)
    run_cmd uv run python -m compileall -q cad_qa scripts tests
    run_cmd uv run pytest -q
    run_suite configs/orchestration_smoke.yaml --list
    run_suite configs/orchestration_smoke.yaml --dry-run
    run_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run
    ;;
  list)
    manifest="${1:-configs/overnight_experiment_suite.yaml}"
    run_suite "$manifest" --list
    ;;
  smoke)
    run_suite configs/orchestration_smoke.yaml --resume "$@"
    ;;
  smoke-dry-run)
    run_suite configs/orchestration_smoke.yaml --dry-run
    ;;
  canary-dry-run)
    run_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies --dry-run "$@"
    ;;
  canary)
    run_suite configs/overnight_experiment_suite.yaml --run answer_sft_canary --with-dependencies "$@"
    ;;
  monitor)
    runs_dir="${1:-runs}"
    run_python -m scripts.experiments.monitor_experiment_run "$runs_dir"
    ;;
  run)
    if [[ $# -lt 1 ]]; then
      usage >&2
      exit 2
    fi
    manifest="$1"
    shift
    run_suite "$manifest" "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
