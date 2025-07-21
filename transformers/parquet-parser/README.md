# Parquet Parser ETL Transformer

This transformer converts Apache Parquet files to various text-based formats (JSON, CSV, or plain text) using Apache Arrow. It's designed for transforming HuggingFace datasets and other parquet-based data sources into ML-ready formats.

## Features

- **Selective Processing**: Only transforms `.parquet` files, passes other files through unchanged
- **Multiple Output Formats**: JSON Lines, CSV, and human-readable text
- **Mixed Dataset Support**: Safely handles datasets with both parquet and non-parquet files
- **High Performance**: Uses Apache Arrow for efficient parquet parsing
- **Zero-Copy Optimization**: Supports direct-put for bucket-to-bucket transformations

## Supported Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| `json` | `.json` | JSON Lines format (default) - one JSON object per line |
| `csv` | `.csv` | Comma-separated values with headers |
| `txt` or `text` | `.txt` | Tab-separated human-readable format |

## Usage

### Configure Output Format

The transformer supports **two ways** to specify the output format:

1. **Environment Variable** (for offline bucket-to-bucket transforms)
2. **ETL Arguments** (for inline single-object transforms)

**Priority**: ETL args override environment variable when both are provided.

#### Method 1: Environment Variable (Offline Transforms)

Set the `OUTPUT_FORMAT` environment variable in your ETL spec:

```yaml
# etl_spec.yaml
name: parquet-parser-etl
runtime:
  image: aistorage/transformer_parquet-parser:latest
  env:
  - name: OUTPUT_FORMAT
    value: "csv"  # Options: json, csv, txt, text
```

#### Method 2: ETL Arguments (Inline Transforms)

Pass the format via `--etl-args` flag:

```bash
# Override with ETL args (takes priority)
ais etl object parquet-parser-etl ais://data/file.parquet output.csv --etl-args csv
```

### Initialize the ETL

```bash
# Navigate to the transformer directory
cd ais-etl/transformers/parquet-parser/

# Deploy the ETL to your AIStore cluster
ais etl init spec --from-file etl_spec.yaml parquet-parser
```

### Transform Data

#### Inline Transformation (Single File)
```bash
# Transform a single parquet file to JSON (using env var default)
ais etl object parquet-parser ais://data/dataset.parquet output.json

# Transform to CSV format (ETL args override env var)
ais etl object parquet-parser ais://data/dataset.parquet output.csv --etl-args csv

# Transform to text format (ETL args override env var)
ais etl object parquet-parser ais://data/dataset.parquet output.txt --etl-args text
```

#### Batch Transformation (Entire Bucket)
```bash
# Transform all parquet files using env var format (set in etl_spec.yaml)
ais etl bucket parquet-parser ais://raw-data/ ais://processed-data/

# Note: ETL args are not supported for bucket-to-bucket transforms
# Use environment variable in etl_spec.yaml to configure format
```

### Real-World Examples

#### HuggingFace Squad Dataset
```bash
# Download and transform in separate steps
ais download --hf-dataset squad ais://raw-squad/
ais etl bucket parquet-parser ais://raw-squad/ ais://squad-json/

# Mixed dataset (preserves non-parquet files)
ais download --hf-dataset common_voice ais://common-voice/
ais etl bucket parquet-parser ais://common-voice/ ais://common-voice-processed/
# Result: .mp3 files unchanged, .parquet files → .json
```

#### Custom Parquet Processing
```bash
# Transform existing parquet files
ais put my-data.parquet ais://data/
ais etl bucket parquet-parser ais://data/ ais://processed/
```

## Output Examples

### Input: `dataset.parquet` (Squad format)
```
id | title | context | question | answers
---|-------|---------|----------|--------
123 | "Article" | "Long text..." | "What is X?" | {"text": ["Answer"], "start": [0]}
```

### Output Formats

#### JSON Lines (`json`)
```json
{"id":"123","title":"Article","context":"Long text...","question":"What is X?","answers":{"text":["Answer"],"start":[0]}}
```

#### CSV (`csv`)
```csv
id,title,context,question,answers
123,Article,"Long text...","What is X?","{""text"":[""Answer""],""start"":[0]}"
```

#### Text (`txt`)
```
id	title	context	question	answers
--	-----	-------	--------	-------
123	Article	Long text...	What is X?	{"text":["Answer"],"start":[0]}
```

## Performance

- **Throughput**: Processes large parquet files efficiently using Arrow's columnar operations
- **Memory**: Streaming processing minimizes memory usage
- **Scalability**: Leverages AIStore's distributed processing across all targets
- **Optimization**: Zero-copy direct-put for bucket-to-bucket transformations

## Configuration

### Environment Variables
- `DEFAULT_FORMAT`: Default output format (`json`, `csv`, `txt`) - default: `json`

### ETL Arguments
Pass output format via `--etl-args`:
- `json` - JSON Lines format (default)
- `csv` - Comma-separated values
- `txt` or `text` - Tab-separated text

## Error Handling

- **Invalid Parquet**: Returns error with descriptive message
- **Unsupported Format**: Returns error for unknown output formats
- **Non-Parquet Files**: Passed through unchanged (no error)
- **Mixed Datasets**: Only parquet files transformed, others preserved

## Building from Source

```bash
# Build the container locally
make build

# Push to registry (requires permissions)
make push

# Custom registry
REGISTRY_URL=your-registry.com make build
```

## Integration with Download Pipeline

This transformer is designed to work with the upcoming AIStore download-ETL pipeline:

```bash
# Future: Single command download + transform
ais download --hf-dataset squad ais://training-data/ \
  --etl-transform parquet-parser \
  --etl-format json
```