# Batch Rename Transformer

The **Batch Rename Transformer** reads objects from a source bucket, and if their path matches a given regex pattern, it writes them to a destination bucket with a modified name (prefixed path). This is useful in ETL pipelines where data normalization, path restructuring, or archival tagging is needed. 

Even if an object does not match the pattern, the transformer still returns the original object bytes to the caller. This allows it to support both inline and offline transformation modes seamlessly.

Its basically a copy operation, your data will be copied to new path. Users are responsible for deleting the old objects.

The transformer supports both `hpull` and `hpush` communication mechanisms, enabling seamless integration into AIStore-based pipelines.

> For more information on ETL communication mechanisms, see [AIStore ETL Documentation](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms).

---

### Environment Variables

| Variable              | Description                                               | Required |
| --------------------- | --------------------------------------------------------- | -------- |
| `AIS_ENDPOINT`        | URL of the AIStore proxy (e.g., `http://ais-proxy:51080`) | ✅ Yes    |
| `DST_BUCKET`          | Name of the destination bucket                            | ✅ Yes    |
| `DST_BUCKET_PROVIDER` | Provider for the destination bucket (default: `ais`)      | No       |
| `FILE_PATTERN`        | Regex pattern to match source object names                | ✅ Yes    |
| `DST_PREFIX`          | Prefix to prepend to renamed object paths                 | ✅ Yes    |

---

### Initializing ETL with AIStore CLI

Follow these steps to initialize the batch rename transformer using the [AIStore CLI](https://github.com/NVIDIA/aistore/blob/main/docs/cli.md):

```bash
$ cd transformers/batch_rename

# Set communication type: either 'hpull://' or 'hpush://'
$ export COMMUNICATION_TYPE='hpull://'

# Initialize the ETL with a chosen name
$ ais etl init spec --from-file etl_spec.yaml

# Inline transformation (single object)
# If the object matches the pattern, it will be renamed and saved to the destination bucket.
# The content will also be returned to the caller.
$ ais etl object <etl-name> ais://<src-bucket>/<object-name> -

# (Optional) Discard content if not needed
$ ais etl object <etl-name> ais://<src-bucket>/<object-name> /dev/null

# To run transformation offline (bucket-to-bucket)
$ ais etl bucket <etl-name> ais://<src-bucket> ais://<dst-bucket>
```
