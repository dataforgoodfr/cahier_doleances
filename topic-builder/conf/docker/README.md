# vLLM Docker Compose configs

Each file defines a single vLLM service.
All variants extend `docker-compose.base.yml`, which holds shared settings (NVIDIA runtime, HuggingFace cache mount, port 8000, host IPC).
This was tested with vLLM `v0.25.1` on a 8GB RTX3070 GPU.

## Available models

| File | Model |
| --- | --- |
| `docker-compose.qwen3-0.6b.yml` | Qwen/Qwen3-0.6B |
| `docker-compose.qwen3.5-2b.yml` | Qwen/Qwen3.5-2B |
| `docker-compose.qwen3-4b-instruct-fp8.yml` | Qwen/Qwen3-4B-Instruct-2507-FP8 |

## Usage

Run from the repo root:

```bash
docker compose -f conf/docker/docker-compose.qwen3-4b-instruct-fp8.yml up
```

Run in the background:

```bash
docker compose -f conf/docker/docker-compose.qwen3-4b-instruct-fp8.yml up -d
```

Stop and remove the container:

```bash
docker compose -f conf/docker/docker-compose.qwen3-4b-instruct-fp8.yml down
```
