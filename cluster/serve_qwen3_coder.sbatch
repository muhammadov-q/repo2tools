#!/bin/bash
# Serve Qwen3-Coder-30B with vLLM, for writing tools with repo2tools.py. Free gratis account, one
# H100 (96 GB). repo2tools.py only needs plain text from this model, so tool calling stays off.
#SBATCH --job-name=vllm-qwen3-coder
#SBATCH --account=gratis
#SBATCH --qos=job_gratis
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --nodes=1
#SBATCH --mem=88G
#SBATCH --time=05:00:00
#SBATCH --output=%x-%j.out

set -euo pipefail
echo "node=$(hostname) port=8000 start=$(date -Is)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
export HF_HOME="${HF_HOME:-/storage/scratch/users/$USER/hf}"
export HF_HUB_OFFLINE=1  # weights were downloaded on the login node
export VLLM_USE_FLASHINFER_SAMPLER=0  # its JIT build needs nvcc, which the GPU nodes lack
source "$HOME/envs/vllm/bin/activate"
exec vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --served-model-name qwen3-coder \
  --host 0.0.0.0 --port 8000 \
  --api-key "$(cat "$HOME/.vllm_api_key")" \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.92
