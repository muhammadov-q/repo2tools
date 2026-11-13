# Serving a model on UBELIX

UBELIX is the University of Bern's HPC cluster. These steps serve Qwen3-8B with vLLM on one RTX 4090, on the free `gratis` account. GPU jobs run for at most 24 hours. If SSH times out, check that you're on the university network or VPN.

## Once, on the login node

```sh
python3 -m pip install --user uv
export PATH="$HOME/.local/bin:$PATH"

# --managed-python matters: the system Python has no Python.h, and vLLM's startup compile needs it
uv venv --managed-python --python 3.12 ~/envs/vllm
uv pip install --python ~/envs/vllm/bin/python vllm

mkdir -p /storage/scratch/users/$USER/hf ~/vllm
HF_HOME=/storage/scratch/users/$USER/hf uvx --from huggingface_hub hf download Qwen/Qwen3-8B
(umask 077; openssl rand -hex 24 > ~/.vllm_api_key)
```

## Each time

Copy `serve_qwen3_8b.sbatch` to `~/vllm/` on the cluster, then:

```sh
cd ~/vllm && sbatch serve_qwen3_8b.sbatch
squeue -u $USER   # shows the node once the job runs; the model takes a few minutes to load
```

From your own computer, open a tunnel to that node and run the model through it:

```sh
ssh -N -L 18000:<node>:8000 <your UBELIX login>
export OPENAI_API_KEY=<contents of ~/.vllm_api_key on the cluster>
# the endpoint is now http://127.0.0.1:18000/v1
```

## A code model for writing tools

``repo2tools generate`` gets better code from a code model. `serve_qwen3_coder.sbatch` serves Qwen3-Coder-30B on one H100. Download it first, as above, with `hf download Qwen/Qwen3-Coder-30B-A3B-Instruct`. It needs about 57 GB of scratch space. A good setup is two jobs and two tunnels: Qwen3-Coder writes the tools, and Qwen3-8B uses them.

```sh
ssh -N -L 18000:<RTX 4090 node>:8000 -L 18001:<H100 node>:8000 <your UBELIX login>
```

Cancel jobs when you finish: `scancel <job id>`.

## A general model for ToolGym

ToolGym's pipeline needs one model that writes text and also calls tools. `serve_qwen3_32b.sbatch` serves Qwen3-32B on one H100 (download: `hf download Qwen/Qwen3-32B`, 65 GB), with tool calling on. Thinking is off by default there, through a changed chat template, because ToolGym cannot switch it off per request.

The free H100 quota is shared by everyone on `gratis`. When it's full, `squeue` shows the reason `QOSGrpGRES` and the job waits. The top of the script shows two ways out: the preemptable partition (free, started within a minute on 11 November 2026, but it can be stopped at any time), or the 8B model on an RTX 4090.

## Good to know

- `sbatch` refuses `--mem` without `--nodes`.
- One H100 allows at most 16 CPUs and 92,160 MB of RAM, so `--mem=96G` is refused.
- `VLLM_USE_FLASHINFER_SAMPLER=0` is needed: FlashInfer's sampler compiles itself on first use and needs `nvcc`, which the GPU nodes don't have.
- All H100s can be busy while RTX 4090s are free. On a 4090, Qwen3-8B leaves about 3.1 GiB for the KV cache: 22,672 tokens, or about 1.4 full-length requests at once.
