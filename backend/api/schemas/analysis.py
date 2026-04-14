from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    channels: list[str] = Field(min_length=2)
    tweets_per_channel: int = 10
    min_channels_for_match: int = 2
    reply_count: int = 20
    twitter_auth_token: str = ""
    twitter_ct0: str = ""


class MatchRequest(BaseModel):
    channels: list[str] = Field(min_length=2)
    tweets_per_channel: int = 10
    min_channels_for_match: int = 2


class AnalysisGroup(BaseModel):
    topic: str
    channels: list[str]
    channel_count: int
    total_reply_count: int = 0
    tweets: list[dict] = Field(default_factory=list)
    replies_by_channel: dict[str, list[dict]] = Field(default_factory=dict)
    emotion_results: dict[str, dict] = Field(default_factory=dict)


class RepliesRequest(BaseModel):
    matched_groups: list[AnalysisGroup]
    reply_count: int = 20
    twitter_auth_token: str = ""
    twitter_ct0: str = ""


class AnalysisResponse(BaseModel):
    matched_groups: list[AnalysisGroup]
    total_groups: int
    total_replies: int
    status: str


class MatchResponse(BaseModel):
    matched_groups: list[AnalysisGroup]
    total_groups: int
    status: str


class RepliesResponse(BaseModel):
    matched_groups: list[AnalysisGroup]
    total_groups: int
    total_replies: int
    status: str


class SentimentCompareRequest(BaseModel):
    matched_groups: list[AnalysisGroup]
    algorithms: list[str] = Field(default_factory=lambda: ["bert", "hybrid"])
    save_to_json: bool = True


class SentimentCompareGroupResult(BaseModel):
    topic: str
    channels: list[str]
    channel_results: dict[str, dict]


class SentimentCompareResponse(BaseModel):
    compared_groups: list[SentimentCompareGroupResult]
    total_groups: int
    status: str
    saved_file: str | None = None


class DualModelCompareRequest(BaseModel):
    source_file: str = "data/yorumlar.json"
    limit: int = 50
    model_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "savasy_bert": 0.55,
            "cardiff_xlm_roberta": 0.45,
        }
    )
    save_to_json: bool = True


class DualModelCompareResponse(BaseModel):
    source_file: str
    requested_limit: int
    compared_count: int
    models: dict[str, dict]
    ensemble: dict
    comments: list[dict]
    status: str
    saved_file: str | None = None
