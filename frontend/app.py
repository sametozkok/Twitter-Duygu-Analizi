"""
Twitter Haber Karşılaştırma & Duygu Analizi - Streamlit Arayüz
"""
import streamlit as st
import sys
import os
import time

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scraper.tweets import fetch_user_tweets
from backend.scraper.replies import fetch_tweet_replies
from backend.analyzer.matcher import match_news
from backend.analyzer.emotion import analyze_emotions_for_replies

# ─── Sayfa Ayarları ───
st.set_page_config(
    page_title="Twitter Haber Analizi",
    page_icon="📰",
    layout="wide",
)

# ─── CSS ───
st.markdown("""
<style>
    .stApp { max-width: 1240px; margin: 0 auto; }
    .hero {
        background: linear-gradient(135deg, #101a2a 0%, #192b45 100%);
        border: 1px solid #29476d;
        border-radius: 14px;
        padding: 18px 22px;
        margin: 6px 0 18px 0;
    }
    .hero h2 { margin: 0; color: #eaf3ff; }
    .hero p { margin: 6px 0 0 0; color: #b8d0ea; }
    .mini-card {
        background: #132238;
        border: 1px solid #24466d;
        border-radius: 12px;
        padding: 10px 14px;
        margin: 8px 0;
    }
    .chip {
        display: inline-block;
        background: #20334f;
        border: 1px solid #355b8f;
        color: #d7e9ff;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 12px;
        margin-right: 6px;
    }
    .tweet-card {
        background: #1e2a3a;
        color: #e8e8e8;
        border-left: 4px solid #1DA1F2;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 0 8px 8px 0;
        font-size: 13px;
        line-height: 1.45;
    }
    .tweet-card strong { color: #8ecdf7; }
    .tweet-card small { color: #aaa; }
    .match-card {
        background: #1a2d42;
        color: #e8e8e8;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border: 1px solid #2a5a8a;
    }
    .match-card strong { color: #8ecdf7; }
    .match-card a { color: #5cb8ff; }
    .result-box {
        background: #111c2e;
        border: 1px solid #2a4e7a;
        border-radius: 12px;
        padding: 10px 14px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── Yardımcılar ───
def render_reply_card(reply: dict):
    likes_str = f" · ❤️ {reply.get('likes', 0)}" if reply.get("likes") else ""
    st.markdown(
        f"""<div class=\"tweet-card\">
        <strong>@{reply.get('user', '')}</strong>{likes_str}<br>
        {reply.get('text', '')}
        </div>""",
        unsafe_allow_html=True,
    )


def render_emotion_details(items: list[dict]):
    for item in items:
        st.markdown(
            f"""<div class=\"tweet-card\">
            <strong>@{item.get('user', '')}</strong> · {item.get('label', '-')} · %{item.get('score', 0)*100:.1f}<br>
            {item.get('text', '')}
            </div>""",
            unsafe_allow_html=True,
        )


# ─── Başlık ───
st.markdown("""
<div class="hero">
  <h2>📰 Twitter Haber Karşılaştırma & Yorum Analizi</h2>
  <p>Kanal tweetlerini karşılaştırır, ortak haberleri bulur, yorumları çeker ve haber bazında duygu analizi yapar.</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar: API Key ───
from pathlib import Path
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=True)
_env_key = os.getenv("GEMINI_API_KEY", "")

# .env'den Twitter cookie'lerini oku
_env_auth_token = os.getenv("TWITTER_AUTH_TOKEN", "")
_env_ct0 = os.getenv("TWITTER_CT0", "")

with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")
    
    gemini_key = st.text_input(
        "Gemini API Key",
        value=_env_key,
        type="password",
        help="Google AI Studio'dan ücretsiz alabilirsiniz: https://aistudio.google.com/apikey"
    )
    
    st.divider()
    min_channels_for_match = st.slider(
        "Ortak haber eşiği (en az kanal)",
        min_value=2,
        max_value=10,
        value=2,
        help="Bir haberin ortak sayılması için en az kaç farklı kanalda geçmesi gerektiğini belirler.",
    )
    st.caption(f"Eşik: en az {min_channels_for_match} kanal")
    
    tweet_count = st.slider(
        "Kanal başına tweet sayısı",
        min_value=5, max_value=20, value=10,
    )
    
    st.divider()
    st.markdown("### 🔐 Twitter Oturum")
    st.caption("Yorum çekimi için cookie bilgileri")
    
    with st.expander("Cookie nasıl alınır?", expanded=False):
        st.markdown("""
        1. [x.com](https://x.com)'a giriş yapın
        2. **F12** → **Application** → **Cookies** → `https://x.com`
        3. `auth_token` ve `ct0` değerlerini kopyalayın
        """)
    
    twitter_auth_token = st.text_input(
        "auth_token",
        value=_env_auth_token,
        type="password",
        help="Twitter auth_token cookie değeri",
    )
    twitter_ct0 = st.text_input(
        "ct0",
        value=_env_ct0,
        type="password",
        help="Twitter ct0 cookie değeri",
    )
    
    twitter_logged_in = bool(twitter_auth_token and twitter_ct0)
    if twitter_logged_in:
        st.success("✅ Twitter oturumu aktif")
    else:
        st.warning("⚠️ Cookie girilmedi — yorumlar çekilemez")
    
    reply_count = st.slider(
        "Tweet başına yorum sayısı",
        min_value=5, max_value=50, value=20,
        help="Her eşleşen tweet için kaç yorum çekileceğini belirler.",
    )

# ─── Ana İçerik: Kanal Girişi ───
st.markdown("### 1) 📡 Kanal Linkleri")
st.caption("Karşılaştırmak istediğiniz hesap linklerini girin")

col1, col2, col3 = st.columns(3)
with col1:
    ch1 = st.text_input("Kanal 1", placeholder="https://x.com/pusholder", key="ch1")
with col2:
    ch2 = st.text_input("Kanal 2", placeholder="https://x.com/vaikigundem", key="ch2")
with col3:
    ch3 = st.text_input("Kanal 3", placeholder="https://x.com/traborasyon", key="ch3")

# Ek kanal ekle
with st.expander("➕ Daha fazla kanal ekle"):
    extra = st.text_area(
        "Her satıra bir kanal linki yazın:",
        placeholder="https://x.com/kanal4\nhttps://x.com/kanal5",
        height=80,
    )

# Tüm kanalları topla
channels = [c.strip() for c in [ch1, ch2, ch3] if c.strip()]
if extra:
    channels += [c.strip() for c in extra.strip().split("\n") if c.strip()]

# ─── Analiz Butonu ───
st.divider()

if "group_results" not in st.session_state:
    st.session_state.group_results = []
if "emotion_results" not in st.session_state:
    st.session_state.emotion_results = {}

if st.button("🚀 Analizi Başlat", type="primary", use_container_width=True):
    
    if len(channels) < min_channels_for_match:
        st.error(f"En az {min_channels_for_match} kanal girmelisiniz! (Ayarlar > Ortak haber eşiği)")
        st.stop()
    
    if not gemini_key:
        st.error("Gemini API Key giriniz! (Sol menüden)")
        st.stop()
    
    # ═══════════════════════════════════════
    # AŞAMA 1: Tweet Çekme
    # ═══════════════════════════════════════
    with st.status("📡 Tweetler çekiliyor...", expanded=True) as status:
        
        channels_data = []
        for i, ch_url in enumerate(channels):
            st.write(f"🔄 Kanal {i+1}: `{ch_url}` çekiliyor...")
            result = fetch_user_tweets(ch_url, tweet_count)
            
            if result["error"]:
                st.warning(f"⚠️ {result['username']}: {result['error']}")
            else:
                st.write(f"✅ @{result['username']}: {len(result['tweets'])} tweet çekildi")
            
            channels_data.append(result)
            
            # Kanallar arası bekleme (rate limit)
            if i < len(channels) - 1:
                time.sleep(1.5)
        
        status.update(label="✅ Tweetler çekildi!", state="complete")
    
    # Başarılı kanalları filtrele
    valid_channels = [ch for ch in channels_data if not ch.get("error") and ch.get("tweets")]
    
    if len(valid_channels) < min_channels_for_match:
        st.error(
            f"En az {min_channels_for_match} kanaldan tweet çekilemedi. "
            "Kanal linklerini veya ortak haber eşiğini kontrol edin."
        )
        st.stop()
    
    # Tweet önizleme
    st.markdown("### 2) 📋 Çekilen Tweetler")
    tweet_tabs = st.tabs([f"@{ch['username']} ({len(ch['tweets'])})" for ch in valid_channels])
    for tab, ch in zip(tweet_tabs, valid_channels):
        with tab:
            for tw in ch["tweets"]:
                clean = tw['clean_text'].replace('<', '&lt;').replace('>', '&gt;')
                st.markdown(
                    f'<div class="tweet-card">'
                    f'<strong>{tw["date_formatted"]}</strong><br>'
                    f'{clean}<br>'
                    f'<small>❤️ {tw["likes"]}  🔁 {tw["retweets"]}  💬 {tw["replies"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    
    st.divider()
    
    # ═══════════════════════════════════════
    # AŞAMA 2: Haber Eşleştirme (Gemini)
    # ═══════════════════════════════════════
    if not gemini_key:
        st.warning("⚠️ Gemini API Key girilmedi — haber eşleştirme ve duygu analizi atlanıyor. Sol menüden geçerli bir API key girin.")
        st.stop()
    
    with st.status("🤖 Gemini ile haberler eşleştiriliyor...", expanded=True) as status:
        
        try:
            matched = match_news(valid_channels, gemini_key, min_channels_for_match)
            st.write(f"✅ {len(matched)} ortak haber bulundu!")
            status.update(label=f"✅ {len(matched)} ortak haber eşleştirildi!", state="complete")
        except Exception as e:
            st.error(f"Gemini hatası: {e}")
            status.update(label="❌ Eşleştirme başarısız", state="error")
            st.warning("💡 API key kotası dolmuş olabilir. Google AI Studio'dan yeni key alın: https://aistudio.google.com/apikey")
            st.stop()
    
    if not matched:
        st.warning("Kanallar arasında ortak haber bulunamadı.")
        st.stop()
    
    # ═══════════════════════════════════════
    # AŞAMA 3: Yorum Çekme (analiz butondan sonra)
    # ═══════════════════════════════════════
    group_results = []
    
    if twitter_logged_in:
        with st.status("💬 Eşleşen haberlerin yorumları çekiliyor...", expanded=True) as reply_status:
            for group_idx, group in enumerate(matched):
                replies_by_channel = {}
                total_reply_count = 0
                
                st.write(f"📌 Haber {group_idx + 1}: {group['topic']}")
                for tw in group["tweets"]:
                    replies = fetch_tweet_replies(
                        tw["tweet_id"], tw["channel"],
                        auth_token=twitter_auth_token,
                        ct0=twitter_ct0,
                        max_replies=reply_count,
                    )
                    
                    if replies:
                        st.write(f"  @{tw['channel']}: {len(replies)} yorum bulundu")
                        replies_by_channel[tw["channel"]] = replies
                        total_reply_count += len(replies)
                    else:
                        st.write(f"  @{tw['channel']}: yorum bulunamadı")
                    
                    time.sleep(0.5)
                
                group_results.append({
                    "topic": group["topic"],
                    "channels": group["channels"],
                    "channel_count": group["channel_count"],
                    "tweets": group["tweets"],
                    "replies_by_channel": replies_by_channel,
                    "total_reply_count": total_reply_count,
                })
            
            reply_status.update(label="✅ Yorumlar çekildi. Artık analiz butonunu kullanabilirsiniz.", state="complete")
    else:
        for group in matched:
            group_results.append({
                "topic": group["topic"],
                "channels": group["channels"],
                "channel_count": group["channel_count"],
                "tweets": group["tweets"],
                "replies_by_channel": {},
                "total_reply_count": 0,
            })
    
    st.session_state.group_results = group_results
    st.session_state.emotion_results = {}
    st.success("✅ Çekim tamamlandı. Aşağıdan haber bazlı yorum analizini başlatabilirsiniz.")

# ─── Kalıcı Sonuçlar ───
if st.session_state.group_results:
    st.markdown("### 3) 📊 Eşleşen Haberler ve Analiz")

    total_groups = len(st.session_state.group_results)
    total_replies = sum(group.get("total_reply_count", 0) for group in st.session_state.group_results)
    analyzed_groups = len(st.session_state.emotion_results)

    s1, s2, s3 = st.columns(3)
    s1.metric("Ortak Haber", total_groups)
    s2.metric("Toplam Yorum", total_replies)
    s3.metric("Analiz Tamamlanan", analyzed_groups)
    
    for group_idx, group in enumerate(st.session_state.group_results):
        replies_by_channel = group.get("replies_by_channel", {})
        total_reply_count = group.get("total_reply_count", 0)
        is_analyzed = group_idx in st.session_state.emotion_results

        header_title = (
            f"📌 {group['topic']}  |  "
            f"{group['channel_count']} kanal  |  "
            f"{total_reply_count} yorum  |  "
            f"{'Analiz tamamlandı' if is_analyzed else 'Analiz bekliyor'}"
        )

        with st.expander(header_title, expanded=False):
            chips = "".join([f"<span class='chip'>@{c}</span>" for c in group["channels"]])
            st.markdown(f"<div class='mini-card'>{chips}</div>", unsafe_allow_html=True)

            tab_tweets, tab_replies = st.tabs(["Tweetler", "Yorumlar & Analiz"])

            with tab_tweets:
                tweet_cols = st.columns(min(len(group["tweets"]), 2))
                for i, tw in enumerate(group["tweets"]):
                    with tweet_cols[i % len(tweet_cols)]:
                        st.markdown(f"""<div class="match-card">
                            <strong>@{tw['channel']}</strong><br>
                            {tw['text']}<br>
                            <a href="{tw['url']}" target="_blank">🔗 Tweet'i aç</a>
                        </div>""", unsafe_allow_html=True)

            with tab_replies:
                if replies_by_channel:
                    st.markdown(f"<div class='result-box'><b>💬 Toplam {total_reply_count} yorum bulundu</b></div>", unsafe_allow_html=True)

                    for channel, ch_replies in replies_by_channel.items():
                        with st.expander(f"📡 @{channel} — {len(ch_replies)} yorum", expanded=False):
                            for reply in ch_replies:
                                render_reply_card(reply)

                    analyze_clicked = st.button(
                        "🧠 Bu haberdeki yorumları analiz et",
                        key=f"analyze_group_{group_idx}",
                        use_container_width=True,
                    )

                    if analyze_clicked:
                        with st.status("🧪 Yorum duygu analizi çalışıyor...", expanded=True):
                            channel_results = {}
                            for channel, ch_replies in replies_by_channel.items():
                                channel_results[channel] = analyze_emotions_for_replies(ch_replies)
                            st.session_state.emotion_results[group_idx] = channel_results
                        st.success("✅ Haber bazlı yorum analizi tamamlandı.")

                    if group_idx in st.session_state.emotion_results:
                        st.markdown("#### 📈 Kanal Bazlı Ortalama Skor")
                        for channel, res in st.session_state.emotion_results[group_idx].items():
                            m1, m2, m3 = st.columns(3)
                            m1.metric(f"@{channel} Ortalama Skor", f"{res['avg_score']:.3f}")
                            m2.metric(f"@{channel} Baskın Duygu", res["dominant_emotion"])
                            m3.metric(f"@{channel} Yorum", res["total"])

                            with st.expander(f"@{channel} yorum analiz detayları", expanded=False):
                                render_emotion_details(res.get("details", []))
                else:
                    st.info("💡 Bu haber grubu için yorum bulunamadı veya Twitter cookie bilgisi girilmedi.")
        st.divider()

# ─── Footer ───
st.markdown("---")
st.caption("Twitter Haber Karşılaştırma & Duygu Analizi | Syndication API + Gemini + BERT Türkçe")
