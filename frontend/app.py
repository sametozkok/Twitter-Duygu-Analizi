"""
Twitter Haber Karşılaştırma & Duygu Analizi - Streamlit Arayüz
"""
import streamlit as st
import sys
import os
import time

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.scraper.tweets import fetch_user_tweets, fetch_multiple_channels
from backend.scraper.replies import fetch_tweet_replies
from backend.analyzer.matcher import match_news
from backend.analyzer.sentiment import analyze_replies

# ─── Sayfa Ayarları ───
st.set_page_config(
    page_title="Twitter Haber Analizi",
    page_icon="📰",
    layout="wide",
)

# ─── CSS ───
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .tweet-card {
        background: #1e2a3a;
        color: #e8e8e8;
        border-left: 4px solid #1DA1F2;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        font-size: 14px;
        line-height: 1.5;
    }
    .tweet-card strong { color: #8ecdf7; }
    .tweet-card small { color: #aaa; }
    .positive { border-left-color: #28a745; }
    .negative { border-left-color: #dc3545; }
    .match-card {
        background: #1a2d42;
        color: #e8e8e8;
        padding: 16px;
        border-radius: 8px;
        margin: 12px 0;
        border: 1px solid #2a5a8a;
    }
    .match-card strong { color: #8ecdf7; }
    .match-card a { color: #5cb8ff; }
</style>
""", unsafe_allow_html=True)

# ─── Başlık ───
st.title("📰 Twitter Haber Karşılaştırma & Duygu Analizi")
st.markdown("Farklı haber kanallarının tweetlerini karşılaştır, ortak haberleri bul ve yorum duygu analizi yap.")
st.divider()

# ─── Sidebar: API Key ───
from pathlib import Path
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=True)
_env_key = os.getenv("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    
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
    st.caption(f"Seçili eşik: En az {min_channels_for_match} kanal")
    
    tweet_count = st.slider(
        "Kanal başına tweet sayısı",
        min_value=5, max_value=20, value=10,
    )

# ─── Ana İçerik: Kanal Girişi ───
st.header("📡 Kanal Linkleri")
st.markdown("Takip etmek istediğiniz Twitter/X kanallarının linklerini yapıştırın:")

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
    
    # Tweet önizleme — her zaman göster
    st.header("📋 Çekilen Tweetler")
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
    # AŞAMA 3: Yorum Çekme & Duygu Analizi
    # ═══════════════════════════════════════
    st.header("📊 Sonuçlar")
    
    for group_idx, group in enumerate(matched):
        st.subheader(f"📌 {group['topic']}")
        st.caption(f"Kanallar: {', '.join(['@' + c for c in group['channels']])} ({group['channel_count']} kanal)")
        
        # Eşleşen tweetleri göster
        tweet_cols = st.columns(min(len(group["tweets"]), 3))
        for i, tw in enumerate(group["tweets"]):
            with tweet_cols[i % len(tweet_cols)]:
                st.markdown(f"""<div class="match-card">
                    <strong>@{tw['channel']}</strong><br>
                    {tw['text']}<br>
                    <a href="{tw['url']}" target="_blank">🔗 Tweet'i aç</a>
                </div>""", unsafe_allow_html=True)
        
        # Her tweet için yorumları çek ve analiz et
        with st.status(f"💬 Yorumlar çekiliyor ve analiz ediliyor...", expanded=False) as reply_status:
            
            all_replies_for_group = []
            
            for tw in group["tweets"]:
                replies = fetch_tweet_replies(tw["tweet_id"], tw["channel"])
                
                if replies:
                    st.write(f"  @{tw['channel']}: {len(replies)} yorum bulundu")
                    all_replies_for_group.extend(replies)
                else:
                    st.write(f"  @{tw['channel']}: yorum bulunamadı")
            
            if all_replies_for_group:
                st.write(f"🔄 {len(all_replies_for_group)} yorum analiz ediliyor...")
                sentiment_result = analyze_replies(all_replies_for_group)
                reply_status.update(label=f"✅ {sentiment_result['total']} yorum analiz edildi", state="complete")
            else:
                sentiment_result = None
                reply_status.update(label="⚠️ Yorum bulunamadı", state="complete")
        
        # Duygu analizi sonuçları
        if sentiment_result and sentiment_result["total"] > 0:
            col_chart, col_stats = st.columns([2, 1])
            
            with col_chart:
                import plotly.graph_objects as go
                
                fig = go.Figure(data=[go.Pie(
                    labels=["Pozitif", "Negatif"],
                    values=[sentiment_result["positive"], sentiment_result["negative"]],
                    marker_colors=["#28a745", "#dc3545"],
                    hole=0.4,
                    textinfo="label+percent",
                )])
                fig.update_layout(
                    title=f"Duygu Dağılımı ({sentiment_result['total']} yorum)",
                    height=350,
                    margin=dict(t=50, b=20, l=20, r=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_stats:
                st.metric("Toplam Yorum", sentiment_result["total"])
                st.metric("🟢 Pozitif", f"{sentiment_result['positive']} ({sentiment_result['positive_pct']}%)")
                st.metric("🔴 Negatif", f"{sentiment_result['negative']} ({sentiment_result['negative_pct']}%)")
            
            # Yorum detayları
            with st.expander("💬 Yorum Detayları"):
                for d in sentiment_result["details"]:
                    css_class = "positive" if d["label"] == "positive" else "negative"
                    st.markdown(f"""<div class="tweet-card {css_class}">
                        {d['emoji']} <strong>@{d['user']}</strong> [%{d['score']*100:.0f}]<br>
                        {d['text']}
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("Bu haber grubu için yorum bulunamadı. Twitter giriş yapmadan yorum erişimi kısıtlı olabilir.")
        
        st.divider()
    
    st.success("✅ Tüm analizler tamamlandı!")

# ─── Footer ───
st.markdown("---")
st.caption("Twitter Haber Karşılaştırma & Duygu Analizi | Syndication API + Gemini + BERT Türkçe")
