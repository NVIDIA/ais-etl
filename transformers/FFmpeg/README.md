# NeMo FFmpeg Transformer

This transformer is used to transform audio files into WAV format with control over Audio Channels (`AC`) and Audio Rate (`AR`). It is based on [NeMo's Speech Data Processor (SDP) Toolkit](https://github.com/NVIDIA/NeMo-speech-data-processor).

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
   ais etl init spec --from-file etl_spec.yaml
   ```

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

## **Performance**

This transformer achieves significantly better performance than traditional FFmpeg methods by leveraging **AIStore’s parallelization** across multiple nodes and ETL communication mechanisms.

### **Performance Highlights**
- **Up to 5x faster** than traditional FFmpeg.
- Performance scales **linearly** with the number of AIStore targets, as objects are distributed across more transformation pods.

### **Benchmark Results**
We benchmarked the transformation of **300 audio files** (each **10 MiB**) using different ETL communication mechanisms:

| **ETL Mode**      | **Time Taken** |
|-------------------|---------------|
| **hpull**         | **46 sec**     |
| **hpush**         | **48 sec**     |
| **hpull with FQN** | **50 sec**     |

For comparison, we tested against:
1. **Python-based FFmpeg script** ('[benchmark.py](benchmark.py)' which is based on [NeMo's Speech Data Processor](https://github.com/NVIDIA/NeMo-speech-data-processor)):  
   - **Time Taken**: **4 min 2.78 sec** (Sequential processing)  
   
2. **FFmpeg Linux CLI Utility**:  
   ```bash
   time bash -c '
   mkdir -p tmp1
   for i in {0..299}; do
       ffmpeg -i audio000.m4a -map 0:a -ac 2 -ar 44100 -c:a pcm_s16le "tmp1/output_audio$i.wav"
   done
   '
   ```
   - **Time Taken**: **3 min 23.71 sec**  
