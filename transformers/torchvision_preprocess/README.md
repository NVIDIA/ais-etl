# Torchvision Image Pre-Processing Transformer

The Torchvision Image Pre-Processing Transformer leverages [torchvision](https://pytorch.org/vision/stable/index.html)'s extensive suite of transformations to process images. By accepting a JSON string of parameter-value pairs, it allows users to define a series of image transformations that correspond directly to [torchvision](https://pytorch.org/vision/stable/index.html)'s native functions. For those already familiar with [torchvision](https://pytorch.org/vision/stable/index.html) and [PyTorch](https://pytorch.org/), this transformer offers a sense of familiarity and ease of use.

This sample transformer supports `hpull`and `hpush` communication mechanisms.

> For more information on communication mechanisms, please refer [here](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

## Parameters

You can customize the behavior of the Torchvision Image Pre-Processing Transformer by setting the `TRANSFORM` and `FORMAT` environment variables.

| Argument    | Description                                                                                     |
|-------------|-------------------------------------------------------------------------------------------------|
| `TRANSFORM` | Specifies a JSON string (dictionary) of PyTorch image transformations to be applied to the input data. |
| `FORMAT`    | Specifies the output image format as a string (e.g., "JPEG", "PNG"). |


These variables should be set according to your specific requirements. The JSON string for `TRANSFORM` should follow the format of PyTorch's torchvision transformations.

> **Note:** Please refer to the [torchvision documentation](https://pytorch.org/vision/stable/transforms.html) for more information on available transformations.

## Usage Examples

### Initializing ETL with AIStore CLI

The following steps demonstrate how to initialize the Torchvision Image Pre-Processing Transformer using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md).

```bash
cd transformers/torch_preprocess

# Set the AIS target URL
export AIS_TARGET_URL="http://localhost:8080"

# Export Communication Mechanism as Environment Variable
export COMMUNICATION_TYPE = 'hpull://'

# Export Transformations as Environment Variable
export TRANSFORM = '{"Resize": {"size": [100, 100]}, "Grayscale": {"num_output_channels": 1}}'

# Export Output Format as Environment Variable
export FORMAT = "JPEG"

# Substitute Environment Variables in Pod Spec
eval "echo \"$(cat pod.yaml)\"" > torch_preprocess_pod_config.yaml 

# Initialize ETL
ais etl init spec --name torch-preprocess-etl --from-file torch_preprocess_pod_config.yaml
```

### Initializing ETL with AIStore Python SDK

The following steps demonstrate how to initialize the Torchvision Image Pre-Processing Transformer using the [AIStore Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md).


```python
import json

from aistore.sdk.client import Client
# Import TORCHVISION Transformer YAML Specification
from aistore.sdk.etl_templates import TORCHVISION_TRANSFORMER
# Import Communication Mechanism
from aistore.sdk.etl_const import ETL_COMM_HPULL

AIS_ENDPOINT = os.environ.get("AIS_ENDPOINT")
client = Client(AIS_ENDPOINT)

# TORCHVISION Options
torchvision_options = json.dumps({"Resize": {"size": [100, 100]}, "Grayscale": {"num_output_channels": 1}})

# Format Template w/ Communication Mechanism & Additional Server Arguments
torchvision_template = TORCHVISION_TRANSFORMER.format(communication_type=ETL_COMM_HPULL, format="JPEG", transform=torchvision_options)

# Initialize ETL 
torchvision_etl = client.etl("torchvision-etl").init_spec(template=torchvision_template, communication_type=ETL_COMM_HPULL)
```

## References

- [Python SDK](https://github.com/NVIDIA/aistore/blob/main/python/aistore/sdk/README.md)
- [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md)
- [AIS-ETL](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md)
- [Torchvision](https://pytorch.org/vision/stable/index.html)
- [PyTorch](https://pytorch.org/)


