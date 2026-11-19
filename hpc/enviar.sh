#!/usr/bin/env bash
# Run from the checkout root. Slurm and Python must see the same shared files.
set -euo pipefail
n=${1:-64}
seed=${2:-20261119}
shards=${3:-8}
out=${4:-resultados/mc_${seed}_${n}}
[[ "$n" =~ ^[1-9][0-9]*$ && "$shards" =~ ^[1-9][0-9]*$ && "$seed" =~ ^[0-9]+$ ]] || exit 2
(( shards <= n )) || { echo 'La cantidad de tareas debe ser menor o igual a N.' >&2; exit 2; }
python_bin=${THERMA_PYTHON:-.venv/bin/python}
"$python_bin" hpc/monte_carlo.py sample --n "$n" --seed "$seed" --out "$out"
mkdir -p "$out/logs"
batch=$(sbatch --parsable --array="0-$((shards-1))" --output="$out/logs/%A_%a.log" \
    hpc/monte_carlo.sbatch run "$out" "$shards")
batch=${batch%%;*}
echo "Array: $batch"
merge=$(sbatch --parsable --dependency="afterok:$batch" --output="$out/logs/%j.log" \
    hpc/monte_carlo.sbatch aggregate "$out")
echo "Agregación: ${merge%%;*}"
printf '%s\n' "$batch" "${merge%%;*}" > "$out/jobs.txt"
