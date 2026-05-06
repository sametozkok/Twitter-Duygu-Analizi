from fastapi import APIRouter, HTTPException

from backend.api.schemas.analysis import RunDetail, RunListResponse, RunSummary
from backend.storage.run_store import delete_run, get_run, list_runs

router = APIRouter(tags=["runs"])


@router.get("/runs", response_model=RunListResponse)
def get_runs() -> RunListResponse:
    summaries = [RunSummary(**item) for item in list_runs()]
    return RunListResponse(runs=summaries, total=len(summaries))


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run_detail(run_id: str) -> RunDetail:
    data = get_run(run_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    return RunDetail(**data)


@router.delete("/runs/{run_id}")
def remove_run(run_id: str) -> dict:
    if not delete_run(run_id):
        raise HTTPException(status_code=404, detail="Run bulunamadi.")
    return {"status": "ok", "run_id": run_id}
