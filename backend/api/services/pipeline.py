from backend.api.schemas.analysis import (
    AnalysisGroup,
    AnalysisRequest,
    AnalysisResponse,
    DualModelCompareRequest,
    DualModelCompareResponse,
    MatchRequest,
    MatchResponse,
    RepliesRequest,
    RepliesResponse,
    SentimentCompareGroupResult,
    SentimentCompareRequest,
    SentimentCompareResponse,
)
from backend.analyzer.dual_model_compare import compare_two_models
from backend.analyzer.emotion import analyze_emotions_for_replies
from backend.analyzer.matcher import match_news
from backend.analyzer.sentiment_compare import compare_replies
from backend.preprocess.text_cleaner import prepare_replies
from backend.scraper.replies import fetch_tweet_replies
from backend.scraper.tweets import fetch_multiple_channels
from backend.storage.json_store import save_snapshot
from backend.storage.run_store import (
    create_run,
    update_run_replies,
    update_run_sentiment,
)
from config import GEMINI_API_KEY, GROK_API_KEY, LLM_PROVIDER, TWITTER_AUTH_TOKEN, TWITTER_BEARER_TOKEN, TWITTER_CT0


def run_match_pipeline(request: MatchRequest) -> MatchResponse:
    # Aktif LLM sağlayıcının key'i tanımlı mı kontrol et
    provider = (LLM_PROVIDER or "").strip().lower()
    if provider in {"groq", "grok"}:
        if not GROK_API_KEY:
            raise ValueError("GROQ_API_KEY tanimli degil. Sunucu ortam degiskenlerini kontrol edin.")
    elif provider == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tanimli degil. Sunucu ortam degiskenlerini kontrol edin.")
    elif not GROK_API_KEY and not GEMINI_API_KEY:
        raise ValueError("Hiçbir LLM API key'i tanimli degil (GROQ_API_KEY veya GEMINI_API_KEY).")

    resolved_bearer = (request.twitter_bearer_token or "").strip() or (TWITTER_BEARER_TOKEN or "").strip()
    channels_data = fetch_multiple_channels(
        request.channels,
        request.tweets_per_channel,
        bearer_token=resolved_bearer,
    )
    valid_channels = [channel for channel in channels_data if not channel.get("error") and channel.get("tweets")]

    if not valid_channels:
        error_lines: list[str] = []
        for item in channels_data:
            username = item.get("username") or "-"
            err = item.get("error")
            tweet_count = len(item.get("tweets") or [])
            if err:
                error_lines.append(f"- @{username}: {err}")
            else:
                error_lines.append(f"- @{username}: tweet bulunamadı (0/{tweet_count})")

        raise ValueError(
            "Kanal tweetleri çekilemedi. Genelde `TWITTER_BEARER_TOKEN` eksik/yanlış ya da X tarafı isteği engellediği için olur.\n"
            + "\n".join(error_lines)
        )

    matched_groups = match_news(valid_channels, GEMINI_API_KEY, request.min_channels_for_match)

    group_results: list[AnalysisGroup] = []
    for group in matched_groups:
        group_results.append(
            AnalysisGroup(
                topic=group.get("topic", "-"),
                channels=group.get("channels", []),
                channel_count=group.get("channel_count", 0),
                total_reply_count=0,
                tweets=group.get("tweets", []),
                replies_by_channel={},
                emotion_results={},
            )
        )

    run_id = create_run(
        channels=request.channels,
        matched_groups=[item.model_dump() for item in group_results],
    )

    return MatchResponse(
        matched_groups=group_results,
        total_groups=len(group_results),
        status="ok",
        run_id=run_id,
    )


def run_replies_pipeline(request: RepliesRequest) -> RepliesResponse:
    group_results: list[AnalysisGroup] = []
    total_replies = 0

    resolved_auth_token = (request.twitter_auth_token or "").strip() or (TWITTER_AUTH_TOKEN or "").strip()
    resolved_ct0 = (request.twitter_ct0 or "").strip() or (TWITTER_CT0 or "").strip()
    resolved_bearer = (request.twitter_bearer_token or "").strip() or (TWITTER_BEARER_TOKEN or "").strip()

    for group in request.matched_groups:
        replies_by_channel: dict[str, list[dict]] = {}
        emotion_results: dict[str, dict] = {}
        group_reply_total = 0

        for tweet in group.tweets:
            tweet_id = str(tweet.get("tweet_id") or tweet.get("id") or "").strip()
            if not tweet_id:
                continue

            replies = fetch_tweet_replies(
                tweet_id,
                str(tweet.get("channel", "")),
                auth_token=resolved_auth_token,
                ct0=resolved_ct0,
                bearer_token=resolved_bearer,
                max_replies=request.reply_count,
            )

            if not replies:
                continue

            replies = prepare_replies(replies)
            if not replies:
                continue

            channel_name = str(tweet.get("channel", ""))
            replies_by_channel[channel_name] = replies
            group_reply_total += len(replies)
            emotion_results[channel_name] = analyze_emotions_for_replies(replies)

        total_replies += group_reply_total
        group_results.append(
            AnalysisGroup(
                topic=group.topic,
                channels=group.channels,
                channel_count=group.channel_count,
                total_reply_count=group_reply_total,
                tweets=group.tweets,
                replies_by_channel=replies_by_channel,
                emotion_results=emotion_results,
            )
        )

    response = RepliesResponse(
        matched_groups=group_results,
        total_groups=len(group_results),
        total_replies=total_replies,
        status="ok",
        run_id=request.run_id,
    )

    if request.run_id:
        update_run_replies(
            request.run_id,
            [item.model_dump() for item in response.matched_groups],
            response.total_replies,
        )

    return response


def run_sentiment_compare_pipeline(request: SentimentCompareRequest) -> SentimentCompareResponse:
    compared_groups: list[SentimentCompareGroupResult] = []

    for group in request.matched_groups:
        prepared_replies_by_channel = {}

        for channel_name, replies in group.replies_by_channel.items():
            prepared = prepare_replies(replies)
            if prepared:
                prepared_replies_by_channel[channel_name] = prepared

        if prepared_replies_by_channel:
            from backend.analyzer.sentiment_compare import compare_group_replies
            channel_results = compare_group_replies(prepared_replies_by_channel, request.algorithms)
        else:
            channel_results = {}

        compared_groups.append(
            SentimentCompareGroupResult(
                topic=group.topic,
                channels=group.channels,
                channel_results=channel_results,
            )
        )

    saved_file: str | None = None
    if request.save_to_json:
        snapshot_payload = {
            "total_groups": len(compared_groups),
            "compared_groups": [item.model_dump() for item in compared_groups],
            "algorithms": request.algorithms,
        }
        saved_file = save_snapshot("sentiment_compare", snapshot_payload)

    if request.run_id:
        update_run_sentiment(
            request.run_id,
            [item.model_dump() for item in compared_groups],
            request.algorithms,
        )

    return SentimentCompareResponse(
        compared_groups=compared_groups,
        total_groups=len(compared_groups),
        status="ok",
        saved_file=saved_file,
        run_id=request.run_id,
    )


def run_dual_model_compare_pipeline(request: DualModelCompareRequest) -> DualModelCompareResponse:
    result = compare_two_models(
        source_file=request.source_file,
        limit=request.limit,
        model_weights=request.model_weights,
    )

    saved_file: str | None = None
    if request.save_to_json:
        saved_file = save_snapshot("dual_model_compare", result)

    return DualModelCompareResponse(
        source_file=result["source_file"],
        requested_limit=result["requested_limit"],
        compared_count=result["compared_count"],
        models=result["models"],
        ensemble=result["ensemble"],
        comments=result["comments"],
        status="ok",
        saved_file=saved_file,
    )


def run_analysis_pipeline(request: AnalysisRequest) -> AnalysisResponse:
    match_result = run_match_pipeline(
        MatchRequest(
            channels=request.channels,
            tweets_per_channel=request.tweets_per_channel,
            min_channels_for_match=request.min_channels_for_match,
            twitter_bearer_token=request.twitter_bearer_token,
        )
    )

    replies_result = run_replies_pipeline(
        RepliesRequest(
            matched_groups=match_result.matched_groups,
            reply_count=request.reply_count,
            twitter_auth_token=request.twitter_auth_token,
            twitter_ct0=request.twitter_ct0,
            twitter_bearer_token=request.twitter_bearer_token,
            run_id=match_result.run_id,
        )
    )

    return AnalysisResponse(
        matched_groups=replies_result.matched_groups,
        total_groups=replies_result.total_groups,
        total_replies=replies_result.total_replies,
        status=replies_result.status,
        run_id=match_result.run_id,
    )
