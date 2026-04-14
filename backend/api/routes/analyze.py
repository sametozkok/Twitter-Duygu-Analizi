from fastapi import APIRouter, HTTPException

from backend.api.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    DualModelCompareRequest,
    DualModelCompareResponse,
    MatchRequest,
    MatchResponse,
    RepliesRequest,
    RepliesResponse,
    SentimentCompareRequest,
    SentimentCompareResponse,
)
from backend.api.services.pipeline import (
    run_analysis_pipeline,
    run_dual_model_compare_pipeline,
    run_match_pipeline,
    run_replies_pipeline,
    run_sentiment_compare_pipeline,
)

router = APIRouter(tags=["analysis"])


@router.post("/analysis", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest) -> AnalysisResponse:
    try:
        return run_analysis_pipeline(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/match", response_model=MatchResponse)
def match(request: MatchRequest) -> MatchResponse:
    try:
        return run_match_pipeline(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/replies", response_model=RepliesResponse)
def replies(request: RepliesRequest) -> RepliesResponse:
    try:
        return run_replies_pipeline(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sentiment/compare", response_model=SentimentCompareResponse)
def sentiment_compare(request: SentimentCompareRequest) -> SentimentCompareResponse:
    try:
        return run_sentiment_compare_pipeline(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sentiment/dual-model-compare", response_model=DualModelCompareResponse)
def sentiment_dual_model_compare(request: DualModelCompareRequest) -> DualModelCompareResponse:
    try:
        return run_dual_model_compare_pipeline(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
