# FFMPEG Decoder Transformer

The provided FFMPEG decode transformer is a powerful tool designed for comprehensive data decoding tasks. The transformer leverages the FFMPEG library (making use of the FFMPEG library's capabilities for decoding various media formats and its pipe mechanism), allowing users to specify regular FFMPEG decoding parameters through a JSON string of parameter-value pairs. This parallels/follows the use of the FFMPEG command-line tool or SDK, presenting an intuitive and familiar interface to those already versed with FFMPEG's functionalities.

This sample transformer supports `hpull`, `hpush`, and `hrev` communication mechanisms.

> For more information on communication mechanisms, please refer [here](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md#communication-mechanisms).

## Parameters

In order to customize the behavior of the FFMPEG decode transformer, you can set the `FFMPEG_OPTIONS` environment variable, which allows you to specify regular FFMPEG decoding parameters as a JSON string.

| Argument | Description | Default Value |
|---|---|---|
| `FFMPEG_OPTIONS` | Specifies a JSON string (dictionary) of regular FFMPEG decoding options to be applied to the input data | `{}` |

This variable should be set according to your specific requirements. If `format` is not specified in `FFMPEG_OPTIONS`, the transformer will infer the format of each input stream, and use the same for the output stream.

> **Note:** Please refer to the [FFMPEG documentation](https://ffmpeg.org/ffmpeg.html) for more information on FFMPEG decoding options.

## Usage Examples

The following section demonstrates usage with the sample FFMPEG decode transformer using both the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md) and the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md).

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the provided FFMPEG decode transformer using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md):

```bash
cd transformers/ffmpeg_decoder

# Set the AIS target URL
export AIS_TARGET_URL="http://localhost:8080"

# Export Communication Mechanism as Envrionment Variable
export COMMUNICATION_TYPE = 'hpull://'

# Export FFMPEG Options as Environment Variable
export FFMPEG_OPTIONS = '{"ar": 44100, "ac": 1}'

# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > ffmpeg_pod_config.yaml 

# Initialize ETL
ais etl init spec --name 'ffmpeg-decode-etl' --from-file ffmpeg_pod_config.yaml
```

### Initializing ETL with AIStore Python SDK

The pod YAML specification for the sample FFMPEG decode transformer is included in the AIStore Python SDK under [`aistore.sdk.etl_templates`](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/etl_templates.py).

The following steps demonstrate how to initialize the sample FFMPEG decode transformer using the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md):

```python
import json

from aistore.sdk.client import Client
# Import FFMPEG Transformer YAML Specification
from aistore.sdk.etl_templates import FFMPEG
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

# FFMPEG Options
ffmpeg_options = json.dumps({"format": "wav", "ar": 44100, "ac": 2, "acodec": "pcm_s16le"})

# Format Template w/ Communication Mechanism & Additional Server Arguments
ffmpeg_template = FFMPEG.format(communication_type=ETL_COMM_HPULL, ffmpeg_options=ffmpeg_options)

# Initialize ETL 
ffmpeg_etl = client.etl("ffmpeg-etl").init_spec(template=ffmpeg_template, communication_type=ETL_COMM_HPULL)
```

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/master/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/master/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/master/docs/etl.md)
