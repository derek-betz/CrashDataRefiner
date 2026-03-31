param(
    [int]$Port = 9005,
    [string]$BindHost = "0.0.0.0"
)

$env:PYTHONPATH = (Resolve-Path ".").Path
python -m uvicorn crash_data_refiner.api:app --host $BindHost --port $Port
