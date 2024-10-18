# NeMo FFmpeg Transformer

This transformer is based on [NeMo's Speech Data Processor (SDP) Toolkit](https://github.com/NVIDIA/NeMo-speech-data-processor). It is used to transform audio files into WAV format with control over Audio Channels (`AC`) and Audio Rate (`AR`).

To transform your audio files using this ETL, follow these steps:

## Initialize the ETL

1. **Navigate to the Directory**  
   Go to the directory where the specification ([`pod.yaml`](pod.yaml)) file exists.

   ```bash
   cd ais-etl/transformers/NeMo/FFmpeg/
   ```

2. **Configure AIStore Endpoint**  
   Ensure your `AIS_ENDPOINT` is pointed to the correct AIStore cluster.

3. **Edit Configuration**  
   Edit the `AR` (Audio Rate) and `AC` (Audio Channels) values in the [`pod.yaml`](pod.yaml) file to match your desired output settings.

4. **Initialize the ETL**  
   Run the following command to create the ETL in the AIStore cluster:

   ```bash
   ais etl init spec --from-file pod.yaml --comm-type <communication-type> --name <etl-name>
   ```
   - `<etl-name>`: Name for your ETL.
   - `<communication-type>`: Communication type for your ETL. (ref: [Communication Mechanisms](https://github.com/NVIDIA/aistore/blob/main/docs/etl.md#communication-mechanisms)). Example: `hpull`, `hpush`, etc.

### Arg Type: FQN (Fully Qualified Name)

When initializing the ETL, you can specify the argument type as Fully Qualified Name (FQN) by adding `--arg-type fqn` to the command. Using FQN means that the AIStore target will send the file path of the object to the transformation pod, rather than the object data itself. The transformation pod will then be responsible for opening, reading, transforming, and closing the corresponding file—in this case, the audio files.

**Initialization with FQN:**

```bash
ais etl init spec --from-file pod_with_fqn.yaml --comm-type hpull --arg-type fqn --name <etl-name>
```

- Replace `<etl-name>` with a name for your ETL.
- Use `pod_with_fqn.yaml` as your specification file, which includes the necessary disk attachments.

**Advantages:**

- **Performance Improvement**: Using FQN can provide a slight performance boost because it avoids transferring the object data over the network to the transformation pod.

**Disadvantages:**

- **Disk Attachment Required**: You must attach all the disks that are attached to the AIStore target to the transformation pod. This requires updating the pod specification as shown in [`pod_with_fqn.yaml`](pod_with_fqn.yaml).

## Transform Data Using the ETL

There are two ways to transform data using this ETL:

### 1. Inline Transformation (During GET Request)

Transform a single object and save the output to a file:

```bash
ais etl object <etl-name> <bucket-name>/<object-name> <output-file>.wav
```

- `<etl-name>`: Name of the ETL you initialized.
- `<bucket-name>`: Name of the bucket containing your audio file.
- `<object-name>`: Name of the audio file to transform.
- `<output-file>.wav`: Filename for the transformed WAV file.

This command transforms the specified object and saves it as a WAV file.

### 2. Offline Transformation (Batch Processing)

Transform multiple objects in parallel and save them to another bucket. This method is faster and leverages AIStore's parallelization capabilities.

#### Get Help on the Command

To see all options for the `bucket` command, run:

```bash
ais etl bucket -h
```

#### Sample Command

```bash
ais etl bucket <etl-name> <source-bucket> <destination-bucket> \
  --cont-on-err \
  --num-workers 500 \
  --ext "{wav:wav,opus:wav,m4a:wav}" \
  --prefix=<virtual-sub-directory> \
  --prepend="transformed/"
```

- `<etl-name>`: Name of the ETL you initialized.
- `<source-bucket>`: Bucket containing the original audio files.
- `<destination-bucket>`: Bucket where transformed files will be saved.
- `--cont-on-err`: Continue processing even if errors occur.
- `--ext "{wav:wav,opus:wav,m4a:wav}"`: Specify input and output file extensions. If you dont specify this, the transformed objects will have the same name and extension.
- `--num-workers 500`: (Optional) Number of parallel workers (adjust as needed).
- `--prefix=<virtual-sub-directory>`: (Optional) Process only files within this sub-directory.
- `--prepend="transformed/"`: (Optional) Prepend this path to the destination objects.

This command transforms all data in the `<source-bucket>` (optionally within the specified virtual sub-directory) and saves it to the `<destination-bucket>`, optionally under the `transformed/` sub-directory.
