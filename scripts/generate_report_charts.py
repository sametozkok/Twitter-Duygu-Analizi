import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ── Türkçe karakter desteği için font ayarı ──
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

os.makedirs("data/report_charts", exist_ok=True)

# ── Veriyi yükle ──
latest_run_path = "data/analysis_runs/sentiment_compare_latest.json"
if not os.path.exists(latest_run_path):
    print(f"Hata: {latest_run_path} bulunamadı!")
    exit(1)

with open(latest_run_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# ── 4 model için toplam duygu sayılarını hesapla ──
ALL_MODELS = ["bert", "roberta", "gemini", "groq"]
MODEL_LABELS = {"bert": "BERT", "roberta": "RoBERTa", "gemini": "Gemini API", "groq": "Groq API"}

model_counts = {m: {"positive": 0, "neutral": 0, "negative": 0} for m in ALL_MODELS}
channel_counts = {}  # kanal -> {duygu -> sayı}

for group in data.get("compared_groups", []):
    for channel, details in group.get("channel_results", {}).items():
        if channel not in channel_counts:
            channel_counts[channel] = {"positive": 0, "neutral": 0, "negative": 0}

        for alg in ALL_MODELS:
            alg_data = details.get("algorithms", {}).get(alg, {})
            if alg_data.get("available") and "summary" in alg_data:
                summary = alg_data["summary"]
                model_counts[alg]["positive"] += summary.get("positive", 0)
                model_counts[alg]["neutral"]  += summary.get("neutral", 0)
                model_counts[alg]["negative"] += summary.get("negative", 0)

                if alg == "bert":
                    channel_counts[channel]["positive"] += summary.get("positive", 0)
                    channel_counts[channel]["neutral"]  += summary.get("neutral", 0)
                    channel_counts[channel]["negative"] += summary.get("negative", 0)

# Sadece available olan modelleri filtrele
active_models = [m for m in ALL_MODELS if sum(model_counts[m].values()) > 0]
print("Aktif modeller:", [MODEL_LABELS[m] for m in active_models])
for m in active_models:
    print(f"  {MODEL_LABELS[m]}: {model_counts[m]}")
print(f"\nKanal bazlı (BERT): {channel_counts}")

# ── Renk paleti ──
COLORS = {"positive": "#27ae60", "neutral": "#f39c12", "negative": "#c0392b"}

# ══════════════════════════════════════════════════════════════
# Grafik 1: Model Karşılaştırması
# ══════════════════════════════════════════════════════════════
labels = [MODEL_LABELS[m] for m in active_models]
pos_vals = [model_counts[m]["positive"] for m in active_models]
neu_vals = [model_counts[m]["neutral"]  for m in active_models]
neg_vals = [model_counts[m]["negative"] for m in active_models]

x = np.arange(len(labels))
width = 0.22

fig, ax = plt.subplots(figsize=(11, 6))
fig.patch.set_facecolor('#fafafa')
ax.set_facecolor('#fafafa')

b1 = ax.bar(x - width, pos_vals, width, label="Pozitif", color=COLORS["positive"], edgecolor='white', linewidth=0.5)
b2 = ax.bar(x,         neu_vals, width, label="Nötr",    color=COLORS["neutral"],  edgecolor='white', linewidth=0.5)
b3 = ax.bar(x + width, neg_vals, width, label="Negatif", color=COLORS["negative"], edgecolor='white', linewidth=0.5)

ax.set_ylabel("Analiz Edilen Yorum Sayısı", fontsize=11, fontweight='bold')
ax.set_title("Duygu Analizi Model Karşılaştırması", fontsize=14, fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(frameon=True, fancybox=True, shadow=True, fontsize=10)
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

def autolabel(bars, axis):
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            axis.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                      str(int(h)), ha='center', va='bottom', fontsize=9, fontweight='bold')

autolabel(b1, ax)
autolabel(b2, ax)
autolabel(b3, ax)

plt.tight_layout()
plt.savefig("data/report_charts/sentiment_comparison.png", dpi=300, bbox_inches='tight')
plt.close()
print("Kaydedildi: data/report_charts/sentiment_comparison.png")

# ══════════════════════════════════════════════════════════════
# Grafik 2: Kanal Bazlı Duygu Dağılımı
# ══════════════════════════════════════════════════════════════
channels_list = list(channel_counts.keys())
if channels_list:
    ch_pos = [channel_counts[ch]["positive"] for ch in channels_list]
    ch_neu = [channel_counts[ch]["neutral"]  for ch in channels_list]
    ch_neg = [channel_counts[ch]["negative"] for ch in channels_list]

    x_ch = np.arange(len(channels_list))

    fig2, ax2 = plt.subplots(figsize=(11, 6))
    fig2.patch.set_facecolor('#fafafa')
    ax2.set_facecolor('#fafafa')

    b_ch1 = ax2.bar(x_ch - width, ch_pos, width, label="Pozitif", color=COLORS["positive"], edgecolor='white', linewidth=0.5)
    b_ch2 = ax2.bar(x_ch,         ch_neu, width, label="Nötr",    color=COLORS["neutral"],  edgecolor='white', linewidth=0.5)
    b_ch3 = ax2.bar(x_ch + width, ch_neg, width, label="Negatif", color=COLORS["negative"], edgecolor='white', linewidth=0.5)

    ax2.set_ylabel("Yorum Sayısı", fontsize=11, fontweight='bold')
    ax2.set_title("Haber Kanallarına Göre Yorum Duygu Dağılımı", fontsize=14, fontweight='bold', pad=15)
    ax2.set_xticks(x_ch)
    ax2.set_xticklabels([f"@{ch}" for ch in channels_list], fontsize=11)
    ax2.legend(frameon=True, fancybox=True, shadow=True, fontsize=10)
    ax2.grid(axis='y', linestyle='--', alpha=0.4)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    autolabel(b_ch1, ax2)
    autolabel(b_ch2, ax2)
    autolabel(b_ch3, ax2)

    plt.tight_layout()
    plt.savefig("data/report_charts/channel_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("Kaydedildi: data/report_charts/channel_comparison.png")
else:
    print("Kanal verisi bulunamadı.")
