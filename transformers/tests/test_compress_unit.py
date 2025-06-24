#!/usr/bin/env python

"""
Integration tests for the Compress ETL Transformer (FastAPI).

Tests the CompressServer functionality including compression, decompression,
and etl_args override capabilities.

Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
"""

import os
import gzip
import bz2
import unittest
from fastapi.testclient import TestClient

# Set environment variables before importing the server
os.environ["AIS_TARGET_URL"] = "http://localhost:8080"
os.environ["COMPRESS_OPTIONS"] = '{"mode": "compress", "compression": "gzip"}'

from compress.fastapi_server import CompressServer


class TestCompressServer(unittest.TestCase):
    """Test cases for CompressServer functionality."""

    def setUp(self):
        """Set up test environment with CompressServer instance."""
        self.etl_server = CompressServer()
        self.client = TestClient(self.etl_server.app)

    def test_health_check(self):
        """Test the health endpoint returns 'Running'."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"Running")

    def test_basic_gzip_compression(self):
        """Test basic gzip compression with default settings."""
        test_data = b"Hello World! This is a test string for compression." * 10
        
        response = self.client.put("/test.txt", content=test_data)
        
        self.assertEqual(response.status_code, 200)
        compressed_data = response.content
        
        # Verify it's actually compressed by decompressing it
        decompressed = gzip.decompress(compressed_data)
        self.assertEqual(decompressed, test_data)
        
        # Compressed data should be smaller for repetitive content
        self.assertLess(len(compressed_data), len(test_data))

    def test_transform_method_directly(self):
        """Test the transform method directly to verify etl_args parsing works."""
        test_data = b"Test data for direct transform"
        
        # Test bz2 compression with etl_args
        result = self.etl_server.transform(test_data, "test.txt", '{"compression":"bz2"}')
        decompressed = bz2.decompress(result)
        self.assertEqual(decompressed, test_data)
        
        # Test decompression with etl_args
        compressed_data = gzip.compress(test_data)
        result = self.etl_server.transform(compressed_data, "test.txt", '{"mode":"decompress"}')
        self.assertEqual(result, test_data)
        
        # Test both mode and compression override
        bz2_compressed = bz2.compress(test_data)
        result = self.etl_server.transform(bz2_compressed, "test.txt", '{"mode":"decompress","compression":"bz2"}')
        self.assertEqual(result, test_data)

    def test_compression_effectiveness(self):
        """Test that compression actually reduces data size for repetitive content."""
        # Create repetitive data that compresses well
        test_data = b"This is repetitive data. " * 100
        
        response = self.client.put("/large_test.txt", content=test_data)
        self.assertEqual(response.status_code, 200)
        compressed_data = response.content
        
        # Verify compression worked
        self.assertLess(len(compressed_data), len(test_data))
        
        # Verify we can decompress it back
        decompressed = gzip.decompress(compressed_data)
        self.assertEqual(decompressed, test_data)


if __name__ == "__main__":
    unittest.main()
