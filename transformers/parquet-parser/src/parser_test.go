/*
 * Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"strings"
	"testing"

	"github.com/apache/arrow-go/v18/arrow"
	"github.com/apache/arrow-go/v18/arrow/array"
	"github.com/apache/arrow-go/v18/arrow/memory"
)

func TestMaxMin(t *testing.T) {
	tests := []struct {
		name  string
		a, b  int
		want  int
		isMax bool
	}{
		{"max 5,3", 5, 3, 5, true},
		{"max 3,5", 3, 5, 5, true},
		{"min 5,3", 5, 3, 3, false},
		{"min 3,5", 3, 5, 3, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got int
			if tt.isMax {
				got = max(tt.a, tt.b)
			} else {
				got = min(tt.a, tt.b)
			}
			if got != tt.want {
				t.Errorf("%s = %v, want %v", tt.name, got, tt.want)
			}
		})
	}
}

func TestConvertTableToFormat(t *testing.T) {
	// Test with nil table
	_, err := convertTableToFormat(nil, FormatJSON)
	if err == nil {
		t.Errorf("convertTableToFormat() with nil table should return error")
	}
}

func TestGetValueFromColumn(t *testing.T) {
	// Test with nil column
	result := getValueFromColumn(nil, 0)
	if result != nil {
		t.Errorf("getValueFromColumn() with nil column should return nil")
	}
}

func TestConvertParquetInvalidFormat(t *testing.T) {
	// Test with invalid format - should fail gracefully
	emptyData := []byte{}
	_, err := convertParquet(emptyData, "invalid")
	if err == nil {
		t.Errorf("convertParquet() with invalid format should return error")
	}
}

// TestDynamicSchemaExtraction tests that headers are extracted from actual schema
func TestDynamicSchemaExtraction(t *testing.T) {
	pool := memory.NewGoAllocator()

	schema := arrow.NewSchema([]arrow.Field{
		{Name: "user_id", Type: arrow.PrimitiveTypes.Int64},
		{Name: "name", Type: arrow.BinaryTypes.String},
		{Name: "score", Type: arrow.PrimitiveTypes.Float64},
	}, nil)

	// Create test data
	userIds := []int64{1, 2, 3}
	names := []string{"Alice", "Bob", "Charlie"}
	scores := []float64{95.5, 87.2, 92.1}

	userIdBuilder := array.NewInt64Builder(pool)
	nameBuilder := array.NewStringBuilder(pool)
	scoreBuilder := array.NewFloat64Builder(pool)

	userIdBuilder.AppendValues(userIds, nil)
	nameBuilder.AppendValues(names, nil)
	scoreBuilder.AppendValues(scores, nil)

	userIdArray := userIdBuilder.NewArray()
	nameArray := nameBuilder.NewArray()
	scoreArray := scoreBuilder.NewArray()
	defer userIdArray.Release()
	defer nameArray.Release()
	defer scoreArray.Release()

	// Create chunked arrays and columns properly
	columns := []arrow.Column{
		*arrow.NewColumn(schema.Field(0), arrow.NewChunked(userIdArray.DataType(), []arrow.Array{userIdArray})),
		*arrow.NewColumn(schema.Field(1), arrow.NewChunked(nameArray.DataType(), []arrow.Array{nameArray})),
		*arrow.NewColumn(schema.Field(2), arrow.NewChunked(scoreArray.DataType(), []arrow.Array{scoreArray})),
	}
	table := array.NewTable(schema, columns, int64(len(userIds)))
	defer table.Release()

	// Verify table was created correctly
	if table.NumRows() != 3 {
		t.Fatalf("Expected 3 rows, got %d", table.NumRows())
	}
	if table.NumCols() != 3 {
		t.Fatalf("Expected 3 columns, got %d", table.NumCols())
	}

	// Test CSV format
	csvData, err := convertToCSV(table)
	if err != nil {
		t.Fatalf("convertToCSV failed: %v", err)
	}

	csvStr := string(csvData)
	if csvStr == "" {
		t.Fatal("CSV output is empty")
	}

	lines := strings.Split(strings.TrimSpace(csvStr), "\n")

	// Verify header is extracted from schema (not hardcoded Squad headers)
	expectedHeader := "user_id,name,score"
	if lines[0] != expectedHeader {
		t.Errorf("CSV header = %q, want %q", lines[0], expectedHeader)
	}

	// Verify data content
	if len(lines) != 4 { // header + 3 data rows
		t.Errorf("Expected 4 lines, got %d. Full output:\n%s", len(lines), csvStr)
	}

	// Test that it's NOT Squad-specific headers
	if strings.Contains(csvStr, "id,title,context,question,answers") {
		t.Error("Found hardcoded Squad headers - should be dynamic!")
	}
}

// TestMergeChunksWithSchema tests that mergeChunks uses dynamic schema
func TestMergeChunksWithSchema(t *testing.T) {
	// Create test schema
	schema := arrow.NewSchema([]arrow.Field{
		{Name: "product_id", Type: arrow.PrimitiveTypes.Int32},
		{Name: "category", Type: arrow.BinaryTypes.String},
	}, nil)

	// Test chunk data (without headers)
	chunkData := [][]byte{
		[]byte("1,Electronics\n"),
		[]byte("2,Books\n"),
	}

	// Test CSV merge
	result, err := mergeChunks(chunkData, FormatCSV, schema)
	if err != nil {
		t.Fatalf("mergeChunks failed: %v", err)
	}

	resultStr := string(result)
	lines := strings.Split(strings.TrimSpace(resultStr), "\n")

	// Verify dynamic header generation
	expectedHeader := "product_id,category"
	if lines[0] != expectedHeader {
		t.Errorf("CSV header = %q, want %q", lines[0], expectedHeader)
	}

	// Verify no hardcoded Squad headers
	if strings.Contains(resultStr, "id,title,context,question,answers") {
		t.Error("Found hardcoded Squad headers in merged output!")
	}
}

// TestFormatConstants verifies our constants are used correctly
func TestFormatConstants(t *testing.T) {
	validFormats := []string{FormatJSON, FormatCSV, FormatTXT, FormatText}

	for _, format := range validFormats {
		t.Run("format_"+format, func(t *testing.T) {
			// This would fail with invalid format
			_, err := convertParquet([]byte{}, format)
			// We expect it to fail due to invalid parquet data, not invalid format
			if err != nil && strings.Contains(err.Error(), "unsupported output format") {
				t.Errorf("Format %q should be supported", format)
			}
		})
	}
}
