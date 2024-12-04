# NeMo - Transformer for Splitting Audio Files

This transformer allows users to split long audio files into smaller segments based on a JSON manifest. This is useful when only specific parts of an audio file are needed for training. The specified segments are extracted from the main audio file, consolidated, and returned as a tarball.

## **How It Works**
1. **Input Manifest**: Provide a JSONL file where each JSON object specifies:
   - **`id`**: Identifier for the audio file.
   - **`part`**: Part number for the segment.
   - **`start_time`** and **`end_time`**: Duration (in seconds) to extract.

2. **Environment Variables**:
   - Configure where the audio files are stored using the following environment variables:
     - **`AIS_ENDPOINT`**: Endpoint of the audio storage.
     - **`AIS_BUCKET`**: Bucket containing audio files.
     - **`AIS_PREFIX`**: Prefix path to the audio files.
     - **`AIS_EXTENSION`**: File extension of the audio files (e.g., `wav`).

3. **Output**: The transformer processes the JSONL manifest, trims the specified segments, and consolidates the output into a tarball.

## **Example**

### Input Manifest (`shard1.jsonl`)
```json
{"id": "youtube_vid_id_1", "part": 1, "start_time": 0.36, "end_time": 2.36}
{"id": "youtube_vid_id_1", "part": 2, "start_time": 3.36, "end_time": 9.36}
{"id": "youtube_vid_id_2", "part": 1, "start_time": 0.00, "end_time": 4.00}
```

### Output Tarball (`shard1.tar`)
The tarball will contain the following trimmed audio files:
- `youtube_vid_id_1_1.wav`  
- `youtube_vid_id_1_2.wav`  
- `youtube_vid_id_2_1.wav`  

These files will contain audio trimmed to the specified durations.
