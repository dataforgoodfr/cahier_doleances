#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — override any of these via environment variables, e.g.:
#   INPUT_CSV=data/<csv-file.csv> OUTPUT_DIR=data/<my-docs> LLM_CONFIG=conf/clients/<my-client> bash scripts/recipe.sh
# ---------------------------------------------------------------------------

INPUT_CSV=${INPUT_CSV:-data/sample/dataset.csv}
OUTPUT_DIR=${OUTPUT_DIR:-data/sample/analysis}
LLM_CONFIG=${LLM_CONFIG:-conf/clients/vllm-qwen3-4b-it-fp8.yaml}

DATASET=$INPUT_CSV

DISCOVER_RESULT=$OUTPUT_DIR/taxonomy/taxonomy_0.json

FACTORIZE_RESULT_1=$OUTPUT_DIR/taxonomy/taxonomy_1.json
FACTORIZE_REPORT_1=$OUTPUT_DIR/taxonomy/report_1.json
FACTORIZE_RESULT_2=$OUTPUT_DIR/taxonomy/taxonomy_2.json
FACTORIZE_REPORT_2=$OUTPUT_DIR/taxonomy/report._2json

STRUCTURE_RESULT_1=$OUTPUT_DIR/taxonomy/taxonomy_3.json
STRUCTURE_REPORT_1=$OUTPUT_DIR/taxonomy/report_3.json
STRUCTURE_RESULT_2=$OUTPUT_DIR/taxonomy/taxonomy_4.json
STRUCTURE_REPORT_2=$OUTPUT_DIR/taxonomy/report_4.json

INSTANCES=$OUTPUT_DIR/instances.json

# ---------------------------------------------------------------------------

echo "==> [1/4] discover: $DATASET -> $DISCOVER_RESULT"
uv run topicbuilder discover-topics \
  --dataset-path "$DATASET" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$DISCOVER_RESULT" \
  --chunk-max-words 500

echo "==> [2/4] factorize: $DISCOVER_RESULT -> $FACTORIZE_RESULT_2"
uv run topicbuilder factorize \
  --taxonomy-path "$DISCOVER_RESULT" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$FACTORIZE_RESULT_1" \
  --report-path "$FACTORIZE_REPORT_1" \
  --chunk-size 100

uv run topicbuilder factorize \
  --taxonomy-path "$FACTORIZE_RESULT_1" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$FACTORIZE_RESULT_2" \
  --report-path "$FACTORIZE_REPORT_2" \
  --chunk-size 100

echo "==> [3/4] structure: $FACTORIZE_RESULT_2 -> $STRUCTURE_RESULT_2"
uv run topicbuilder discover-parents \
  --taxonomy-path "$FACTORIZE_RESULT_2" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$STRUCTURE_RESULT_1" \
  --report-path "$STRUCTURE_REPORT_1" \
  --chunk-size 100

uv run topicbuilder discover-parents \
  --taxonomy-path "$STRUCTURE_RESULT_1" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$STRUCTURE_RESULT_2" \
  --report-path "$STRUCTURE_REPORT_2" \
  --chunk-size 100

echo "==> [4/4] label: $DATASET + $STRUCTURE_RESULT_2 -> $INSTANCES"
uv run topicbuilder label \
  --dataset-path "$DATASET" \
  --taxonomy-path "$STRUCTURE_RESULT_2" \
  --llm-config-path "$LLM_CONFIG" \
  --output-path "$INSTANCES" \
  --chunk-max-words 500 \
  --taxonomy-chunk-size 20

echo "Done. Results in $OUTPUT_DIR/"
