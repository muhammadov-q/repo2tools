#!/bin/bash
# Serve Qwen3-32B with vLLM (tool calling on, thinking off by default), for ToolGym's generation
# pipeline and generated_to_toolgym.py. Free gratis account, one H100 (96 GB).
#
# If the gratis H100 quota is full (squeue shows QOSGrpGRES), the same script runs elsewhere:
#   preemptable H100:  sbatch --partition=gpu-invest --qos=job_gpu_preemptable serve_qwen3_32b.sbatch
#   8B on an RTX 4090: sbatch --gres=gpu:rtx4090:1 --mem=48G --job-name=vllm-qwen3-8b \
#                        --export=ALL,MODEL=Qwen/Qwen3-8B,NAME=qwen3-8b,MAXLEN=16384 serve_qwen3_32b.sbatch
#SBATCH --job-name=vllm-qwen3-32b
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
MODEL="${MODEL:-Qwen/Qwen3-32B}"
NAME="${NAME:-qwen3-32b}"
MAXLEN="${MAXLEN:-32768}"

# ToolGym's LLM adapter cannot pass enable_thinking, and Qwen3 thinks by default. So this makes a
# copy of the model's chat template with thinking off, unless a request turns it on.
TEMPLATE="$HOME/vllm/$NAME-no-thinking.jinja"
python - "$TEMPLATE" "$MODEL" <<'PY'
import sys
from transformers import AutoTokenizer
template = AutoTokenizer.from_pretrained(sys.argv[2]).chat_template
open(sys.argv[1], "w").write("{%- if enable_thinking is not defined %}{%- set enable_thinking = false %}{%- endif %}\n" + template)
PY

exec vllm serve "$MODEL" \
  --served-model-name "$NAME" \
  --host 0.0.0.0 --port 8000 \
  --api-key "$(cat "$HOME/.vllm_api_key")" \
  --max-model-len "$MAXLEN" \
  --gpu-memory-utilization 0.92 \
  --chat-template "$TEMPLATE" \
  --enable-auto-tool-choice --tool-call-parser hermes
