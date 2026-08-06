# Process

Prerequisites:

- having done the project setup, see the README.
- having a dataset of cahiers Chabin with columns `id` and `content` at `data/cahiers_chabin/dataset.csv`.
- having a LLM server available, which will be queried using a conf `conf/clients/<your-llm-server>.yaml`).

## 1. Topic Discovery

```sh
docker compose -f conf/docker/docker-compose.qwen3-4b-instruct-fp8.yml up
```

```sh
topicbuilder discover --dataset-path data/cahiers_chabin/dataset.csv --llm-config-path conf/clients/vllm-qwen3-4b-it-fp8.yaml --output-path data/cahiers_chabin/analysis_v3/discover/taxonomy.json
```

## 2. Topic factorization

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/discover/taxonomy.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_1.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_1.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_1.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_2.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_2.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_2.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_3.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_3.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_3.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_4.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_4.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_4.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_5.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_5.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_5.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_6.json --report-path data/cahiers_chabin/analysis_v3/factorize/report_6.json
```

## 3. Parent topic creation

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/factorize/taxonomy_6.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_1.json --report-path data/cahiers_chabin/analysis_v3/structure/report_1.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_1.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_2.json --report-path data/cahiers_chabin/analysis_v3/structure/report_2.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_2.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_3.json --report-path data/cahiers_chabin/analysis_v3/structure/report_3.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_3.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_4.json --report-path data/cahiers_chabin/analysis_v3/structure/report_4.json
```

Factorize this

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_4.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_5.json --report-path data/cahiers_chabin/analysis_v3/structure/report_5.json
```

Check the resulting taxonomy

```sh
topicbuilder display --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_5.json --port 8080
```

Some more parents

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_5.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_6.json --report-path data/cahiers_chabin/analysis_v3/structure/report_6.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_6.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_7.json --report-path data/cahiers_chabin/analysis_v3/structure/report_7.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_7.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_8.json --report-path data/cahiers_chabin/analysis_v3/structure/report_8.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_8.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_9.json --report-path data/cahiers_chabin/analysis_v3/structure/report_9.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_9.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_10.json --report-path data/cahiers_chabin/analysis_v3/structure/report_10.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_10.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_11.json --report-path data/cahiers_chabin/analysis_v3/structure/report_11.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_11.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_12.json --report-path data/cahiers_chabin/analysis_v3/structure/report_12.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_12.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_13.json --report-path data/cahiers_chabin/analysis_v3/structure/report_13.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_13.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_14.json --report-path data/cahiers_chabin/analysis_v3/structure/report_14.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_14.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_15.json --report-path data/cahiers_chabin/analysis_v3/structure/report_15.json
```

Less than 20 parents were created here, so we stop. Factorize this

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_15.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_16.json --report-path data/cahiers_chabin/analysis_v3/structure/report_16.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_16.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_17.json --report-path data/cahiers_chabin/analysis_v3/structure/report_17.json
```

Check the resulting taxonomy

```sh
topicbuilder display --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_9.json --port 8080
```

Try creating some more parents

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_17.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_18.json --report-path data/cahiers_chabin/analysis_v3/structure/report_18.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_18.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_19.json --report-path data/cahiers_chabin/analysis_v3/structure/report_19.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_19.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_20.json --report-path data/cahiers_chabin/analysis_v3/structure/report_20.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_20.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_21.json --report-path data/cahiers_chabin/analysis_v3/structure/report_21.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_21.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_22.json --report-path data/cahiers_chabin/analysis_v3/structure/report_22.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_22.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_23.json --report-path data/cahiers_chabin/analysis_v3/structure/report_23.json
```

```sh
topicbuilder structure --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_23.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_24.json --report-path data/cahiers_chabin/analysis_v3/structure/report_24.json
```

Only 10 new parents created at this point. Factorize this

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_24.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_25.json --report-path data/cahiers_chabin/analysis_v3/structure/report_25.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_25.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_26.json --report-path data/cahiers_chabin/analysis_v3/structure/report_26.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_26.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_27.json --report-path data/cahiers_chabin/analysis_v3/structure/report_27.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_27.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_28.json --report-path data/cahiers_chabin/analysis_v3/structure/report_28.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_28.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_29.json --report-path data/cahiers_chabin/analysis_v3/structure/report_29.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_29.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_30.json --report-path data/cahiers_chabin/analysis_v3/structure/report_30.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_30.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_31.json --report-path data/cahiers_chabin/analysis_v3/structure/report_31.json
```

```sh
topicbuilder factorize --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_31.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/structure/taxonomy_32.json --report-path data/cahiers_chabin/analysis_v3/structure/report_32.json
```

Check the resulting taxonomy

```sh
topicbuilder display --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_32.json --port 8080
```

## 4. Labeling

```sh
topicbuilder label --dataset-path data/cahiers_chabin/dataset.csv --taxonomy-path data/cahiers_chabin/analysis_v3/structure/taxonomy_32.json --llm-config-path conf/clients/azure.yaml --output-path data/cahiers_chabin/analysis_v3/label/instances.json
```
