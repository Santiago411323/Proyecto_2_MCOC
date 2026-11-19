#!/usr/bin/env bash
#SBATCH --job-name=therma-mc
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=02:00:00
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python_bin=${THERMA_PYTHON:-.venv/bin/python}
mode=${1:?run or aggregate}
out=${2:?batch directory}
case "$mode" in
    run)
        "$python_bin" -u hpc/monte_carlo.py run --out "$out" \
            --index "${SLURM_ARRAY_TASK_ID:?}" --shards "${3:?number of shards}" \
            --workers "${SLURM_CPUS_PER_TASK:-1}"
        ;;
    aggregate)
        "$python_bin" hpc/monte_carlo.py aggregate --out "$out"
        ;;
    *) exit 2 ;;
esac
