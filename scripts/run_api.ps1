param(
    [int]$Port = 9005,
    [string]$Host = "0.0.0.0"
)

$env:PYTHONPATH = (Resolve-Path ".").Path
python -m uvicorn crash_data_refiner.api:app --host $Host --port $Port
