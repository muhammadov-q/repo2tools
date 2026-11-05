#!/bin/bash
# Serve Qwen3-8B with vLLM as an OpenAI-compatible endpoint (tool calling on) for the
# packaging exercises and ToolGym. Free gratis account, one RTX 4090 (24 GB).
#SBATCH --job-name=vllm-qwen3-8b
#SBATCH --account=gratis
#SBATCH --qos=job_gratis
#SBATCH --partition=gpu
#SBATCH --gres=gpu:rtx4090:1
#SBATCH --cpus-per-task=8
#SBATCH --nodes=1
#SBATCH --mem=48G
#SBATCH --time=05:00:00
#SBATCH --output=%x-%j.out

set -euo pipefail
echo "node=$(hostname) port=8000 start=$(date -Is)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
export HF_HOME="${HF_HOME:-/storage/scratch/users/$USER/hf}"
export HF_HUB_OFFLINE=1  # weights were downloaded on the login node
export VLLM_USE_FLASHINFER_SAMPLER=0  # its JIT build needs nvcc, which the GPU nodes lack
source "$HOME/envs/vllm/bin/activate"
exec vllm serve Qwen/Qwen3-8B \
  --served-model-name qwen3-8b \
  --host 0.0.0.0 --port 8000 \
  --api-key "$(cat "$HOME/.vllm_api_key")" \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.92 \
  --enable-auto-tool-choice --tool-call-parser hermes
