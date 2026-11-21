package shared

import (
	"context"
	"encoding/json"
	"errors"
	"reflect"
	"testing"
)

func TestS01dContractRoundTrip(t *testing.T) {
	request := S01dNormalizeProgramsRequest{
		OutputDirectory:      "runs/run0001/01d",
		ProgramPoolPartPaths: []string{"runs/run0001/01c/pool-000.parquet"},
		ShardIndex:           0,
	}
	result := S01dNormalizeProgramsResult{
		NormalizedPartPath:   "runs/run0001/01d/normalized-000.parquet",
		FailurePartPath:      "runs/run0001/01d/failures-000.parquet",
		NormalizedCount:      10,
		FailureCount:         1,
		NormalizationVersion: "01d-v1",
	}

	payload, err := json.Marshal(S01dNormalizeProgramsContract{Request: request, Result: result})
	if err != nil {
		t.Fatalf("marshal contract: %v", err)
	}

	var decoded S01dNormalizeProgramsContract
	if err := json.Unmarshal(payload, &decoded); err != nil {
		t.Fatalf("unmarshal contract: %v", err)
	}
	if !reflect.DeepEqual(decoded, S01dNormalizeProgramsContract{Request: request, Result: result}) {
		t.Fatalf("round trip = %#v, want request %#v and result %#v", decoded, request, result)
	}
}

func TestPythonWorkerAcceptsTypedS01dRequest(t *testing.T) {
	worker := pythonWorkerForTest(t)

	request := S01dNormalizeProgramsRequest{
		OutputDirectory:      "runs/run0001/01d",
		ProgramPoolPartPaths: []string{"runs/run0001/01c/pool-000.parquet"},
		ShardIndex:           0,
	}
	var response map[string]any
	err := worker.Run(context.Background(), request, &response)
	if err == nil {
		t.Fatal("unimplemented pipeline stage returned no error")
	}

	var workerError *WorkerError
	if !errors.As(err, &workerError) {
		t.Fatalf("error = %v, want *WorkerError", err)
	}
	if workerError.Code != "stage_not_implemented" {
		t.Fatalf("error code = %q, want stage_not_implemented", workerError.Code)
	}
}

func TestPythonWorkerRejectsInvalidS01dRequest(t *testing.T) {
	worker := pythonWorkerForTest(t)

	var response map[string]any
	err := worker.Run(context.Background(), map[string]any{}, &response)
	if err == nil {
		t.Fatal("invalid request returned no error")
	}

	var workerError *WorkerError
	if !errors.As(err, &workerError) {
		t.Fatalf("error = %v, want *WorkerError", err)
	}
	if workerError.Code != "invalid_request" {
		t.Fatalf("error code = %q, want invalid_request", workerError.Code)
	}
}
