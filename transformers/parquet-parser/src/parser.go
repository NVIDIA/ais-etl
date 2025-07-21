// Package main provides parquet parsing functionality
/*
 * Copyright (c) 2025, NVIDIA CORPORATION. All rights reserved.
 */
package main

import (
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"runtime"
	"strings"
	"sync"

	"github.com/NVIDIA/aistore/sys"
	"github.com/apache/arrow-go/v18/arrow"
	"github.com/apache/arrow-go/v18/arrow/memory"
	"github.com/apache/arrow-go/v18/parquet/file"
	"github.com/apache/arrow-go/v18/parquet/pqarrow"
	"golang.org/x/sync/errgroup"
)

const (
	FormatJSON = "json"
	FormatCSV  = "csv"
	FormatTXT  = "txt"
	FormatText = "text"

	ConcurrentThreshold = 1000
)

type ChunkTask struct {
	Index    int
	StartRow int
	EndRow   int
}

type chunkWorker struct {
	table        arrow.Table
	outputFormat string
	results      [][]byte
	mu           *sync.Mutex
}

func (cw *chunkWorker) process(task *ChunkTask) error {
	data, err := processChunk(cw.table, task.StartRow, task.EndRow, cw.outputFormat)
	if err != nil {
		return fmt.Errorf("chunk %d failed: %w", task.Index, err)
	}

	cw.mu.Lock()
	cw.results[task.Index] = data
	cw.mu.Unlock()

	return nil
}

func convertParquet(parquetData []byte, outputFormat string) ([]byte, error) {
	allocator := memory.NewGoAllocator()
	reader := bytes.NewReader(parquetData)

	parquetReader, err := file.NewParquetReader(reader)
	if err != nil {
		return nil, fmt.Errorf("failed to create parquet reader: %w", err)
	}
	defer parquetReader.Close()

	// Create Arrow reader with proper allocator
	arrowReader, err := pqarrow.NewFileReader(parquetReader, pqarrow.ArrowReadProperties{}, allocator)
	if err != nil {
		return nil, fmt.Errorf("failed to create arrow reader: %w", err)
	}

	table, err := arrowReader.ReadTable(context.Background())
	if err != nil {
		return nil, fmt.Errorf("failed to read table: %w", err)
	}
	defer table.Release()

	if table.NumRows() > ConcurrentThreshold {
		return convertTableConcurrent(table, outputFormat)
	}
	// For single row group, use single-threaded approach
	return convertTableToFormat(table, outputFormat)
}

// convertTableConcurrent processes table data using concurrent chunks
func convertTableConcurrent(table arrow.Table, outputFormat string) ([]byte, error) {
	numRows := int(table.NumRows())
	chunkSize := max(100, numRows/runtime.NumCPU())
	numChunks := (numRows + chunkSize - 1) / chunkSize

	// Create worker with shared state
	var mu sync.Mutex
	worker := &chunkWorker{
		table:        table,
		outputFormat: outputFormat,
		results:      make([][]byte, numChunks),
		mu:           &mu,
	}

	// Create tasks
	tasks := make([]*ChunkTask, numChunks)
	for i := 0; i < numChunks; i++ {
		startRow := i * chunkSize
		endRow := min(startRow+chunkSize, numRows)
		tasks[i] = &ChunkTask{
			Index:    i,
			StartRow: startRow,
			EndRow:   endRow,
		}
	}

	eg, _ := errgroup.WithContext(context.Background())
	eg.SetLimit(sys.MaxParallelism())

	for _, task := range tasks {
		task := task // capture pointer
		eg.Go(func() error {
			return worker.process(task)
		})
	}

	if err := eg.Wait(); err != nil {
		return nil, err
	}

	return mergeChunks(worker.results, outputFormat, table.Schema())
}

func processChunk(table arrow.Table, startRow, endRow int, outputFormat string) ([]byte, error) {
	numCols := int(table.NumCols())
	switch outputFormat {
	case FormatJSON:
		return processChunkJSON(table, startRow, endRow, numCols)
	case FormatCSV:
		return processChunkCSV(table, startRow, endRow, numCols)
	case FormatTXT, FormatText:
		return processChunkText(table, startRow, endRow, numCols)
	default:
		return nil, fmt.Errorf("unsupported output format: %s", outputFormat)
	}
}

// processChunkJSON converts a chunk to JSON format
func processChunkJSON(table arrow.Table, startRow, endRow, numCols int) ([]byte, error) {
	var buf bytes.Buffer
	for row := startRow; row < endRow; row++ {
		record := make(map[string]any)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column == nil {
				continue
			}
			field := table.Schema().Field(col)
			record[field.Name] = getValueFromColumn(column, row)
		}
		jsonData, err := json.Marshal(record)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal JSON for row %d: %w", row, err)
		}
		buf.Write(jsonData)
		buf.WriteByte('\n')
	}
	return buf.Bytes(), nil
}

// processChunkCSV converts a chunk to CSV format (no header)
func processChunkCSV(table arrow.Table, startRow, endRow, numCols int) ([]byte, error) {
	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)
	defer writer.Flush()

	for row := startRow; row < endRow; row++ {
		record := make([]string, numCols)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column != nil {
				value := getValueFromColumn(column, row)
				record[col] = fmt.Sprintf("%v", value)
			} else {
				record[col] = ""
			}
		}

		if err := writer.Write(record); err != nil {
			return nil, fmt.Errorf("failed to write CSV row %d: %w", row, err)
		}
	}
	return buf.Bytes(), nil
}

// processChunkText converts a chunk to text format (no header)
func processChunkText(table arrow.Table, startRow, endRow, numCols int) ([]byte, error) {
	var buf bytes.Buffer
	for row := startRow; row < endRow; row++ {
		values := make([]string, numCols)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column != nil {
				value := getValueFromColumn(column, row)
				values[col] = fmt.Sprintf("%v", value)
			} else {
				values[col] = ""
			}
		}
		buf.WriteString(strings.Join(values, "\t"))
		buf.WriteByte('\n')
	}
	return buf.Bytes(), nil
}

// mergeChunks combines processed chunks based on output format
func mergeChunks(chunkData [][]byte, outputFormat string, schema *arrow.Schema) ([]byte, error) {
	if len(chunkData) == 0 {
		return []byte{}, nil
	}

	var result bytes.Buffer
	switch outputFormat {
	case FormatJSON:
		for _, data := range chunkData {
			result.Write(data)
		}
	case FormatCSV:
		// Generate CSV header from schema
		headers := make([]string, schema.NumFields())
		for i := 0; i < schema.NumFields(); i++ {
			headers[i] = schema.Field(i).Name
		}
		result.WriteString(strings.Join(headers, ","))
		result.WriteByte('\n')
		for _, data := range chunkData {
			result.Write(data)
		}
	case FormatTXT, FormatText:
		// Generate text header from schema
		headers := make([]string, schema.NumFields())
		for i := 0; i < schema.NumFields(); i++ {
			headers[i] = schema.Field(i).Name
		}
		result.WriteString(strings.Join(headers, "\t"))
		result.WriteByte('\n')

		// Add separator line
		separators := make([]string, len(headers))
		for i, header := range headers {
			separators[i] = strings.Repeat("-", len(header))
		}
		result.WriteString(strings.Join(separators, "\t"))
		result.WriteByte('\n')

		for _, data := range chunkData {
			result.Write(data)
		}
	default:
		return nil, fmt.Errorf("unsupported output format for merging: %s", outputFormat)
	}
	return result.Bytes(), nil
}

// convertTableToFormat converts Arrow table to specified format
func convertTableToFormat(table arrow.Table, outputFormat string) ([]byte, error) {
	if table == nil {
		return nil, fmt.Errorf("table is nil")
	}

	switch outputFormat {
	case FormatJSON:
		return convertToJSON(table)
	case FormatCSV:
		return convertToCSV(table)
	case FormatTXT, FormatText:
		return convertToText(table)
	default:
		return nil, fmt.Errorf("unsupported output format: %s", outputFormat)
	}
}

// convertToJSON converts Arrow table to JSON Lines format
func convertToJSON(table arrow.Table) ([]byte, error) {
	if table == nil {
		return nil, fmt.Errorf("table is nil")
	}

	var buf bytes.Buffer
	numRows := int(table.NumRows())
	numCols := int(table.NumCols())

	for row := 0; row < numRows; row++ {
		record := make(map[string]any)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column == nil {
				continue
			}
			field := table.Schema().Field(col)
			record[field.Name] = getValueFromColumn(column, row)
		}
		jsonData, err := json.Marshal(record)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal JSON for row %d: %w", row, err)
		}
		buf.Write(jsonData)
		buf.WriteByte('\n')
	}
	return buf.Bytes(), nil
}

// convertToCSV converts Arrow table to CSV format
func convertToCSV(table arrow.Table) ([]byte, error) {
	if table == nil {
		return nil, fmt.Errorf("table is nil")
	}

	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)

	numCols := int(table.NumCols())
	numRows := int(table.NumRows())

	header := make([]string, numCols)
	for i := 0; i < numCols; i++ {
		field := table.Schema().Field(i)
		header[i] = field.Name
	}
	if err := writer.Write(header); err != nil {
		return nil, fmt.Errorf("failed to write CSV header: %w", err)
	}

	// Write rows
	for row := 0; row < numRows; row++ {
		record := make([]string, numCols)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column != nil {
				value := getValueFromColumn(column, row)
				record[col] = fmt.Sprintf("%v", value)
			} else {
				record[col] = ""
			}
		}
		if err := writer.Write(record); err != nil {
			return nil, fmt.Errorf("failed to write CSV row %d: %w", row, err)
		}
	}

	// Explicitly flush the writer before returning in case all rows are not written
	writer.Flush()
	return buf.Bytes(), nil
}

// convertToText converts Arrow table to human-readable text format
func convertToText(table arrow.Table) ([]byte, error) {
	if table == nil {
		return nil, fmt.Errorf("table is nil")
	}

	var buf bytes.Buffer
	numCols := int(table.NumCols())
	numRows := int(table.NumRows())

	// Write column headers
	headers := make([]string, numCols)
	for i := 0; i < numCols; i++ {
		field := table.Schema().Field(i)
		headers[i] = field.Name
	}
	buf.WriteString(strings.Join(headers, "\t"))
	buf.WriteByte('\n')

	// Write separator line
	for i := 0; i < numCols; i++ {
		if i > 0 {
			buf.WriteByte('\t')
		}
		buf.WriteString(strings.Repeat("-", len(headers[i])))
	}
	buf.WriteByte('\n')

	// Write data rows
	for row := 0; row < numRows; row++ {
		values := make([]string, numCols)
		for col := 0; col < numCols; col++ {
			column := table.Column(col)
			if column != nil {
				value := getValueFromColumn(column, row)
				values[col] = fmt.Sprintf("%v", value)
			} else {
				values[col] = ""
			}
		}
		buf.WriteString(strings.Join(values, "\t"))
		buf.WriteByte('\n')
	}
	return buf.Bytes(), nil
}

// getValueFromColumn extracts a value from an Arrow column at the specified row
func getValueFromColumn(column *arrow.Column, row int) any {
	if column == nil {
		return nil
	}

	data := column.Data()
	if data == nil || data.Len() == 0 {
		return nil
	}

	chunkRow := row
	var chunk arrow.Array

	// Find the correct chunk for this row
	for i := 0; i < data.Len(); i++ {
		chunk = data.Chunk(i)
		if chunk == nil {
			continue
		}
		if chunkRow < chunk.Len() {
			break
		}
		chunkRow -= chunk.Len()
		chunk = nil
	}

	if chunk == nil || chunkRow < 0 || chunkRow >= chunk.Len() {
		return nil
	}

	if chunk.IsNull(chunkRow) {
		return nil
	}

	// Always returns primitive values/nulls, no maps/nested structures/user-defined types
	return chunk.GetOneForMarshal(chunkRow)
}
