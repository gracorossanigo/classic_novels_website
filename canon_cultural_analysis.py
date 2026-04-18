import ast
import os
import json
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec
import requests
import seaborn as sns
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import squareform

plt.rcParams['figure.dpi'] = 110
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False


def save_table_png(df, path, title=None, col_widths=None):
    n_rows, n_cols = len(df), len(df.columns)
    row_h, header_h = 0.35, 0.5
    fig_h = header_h + n_rows * row_h + (0.5 if title else 0.1)
    col_widths = col_widths or [max(len(str(c)), df[c].astype(str).str.len().max()) for c in df.columns]
    fig_w = sum(col_widths) * 0.18 + 0.4
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis('off')
    if title:
        fig.suptitle(title, fontsize=10, fontweight='bold', y=0.98)
    tbl = ax.table(
        cellText=df.values,
        colLabels=df.columns.tolist(),
        cellLoc='left', loc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.auto_set_column_width(list(range(n_cols)))
    for (r, _), cell in tbl.get_celld().items():
        cell.set_edgecolor('#e5e7eb')
        if r == 0:
            cell.set_facecolor('#1e3a5f')
            cell.set_text_props(color='white', fontweight='bold')
        elif r % 2 == 0:
            cell.set_facecolor('#f1f5f9')
        else:
            cell.set_facecolor('white')
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)

CACHE_DIR = 'data'
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs('figures', exist_ok=True)

LANGUAGES = {
    'English': 'en', 'French': 'fr', 'German': 'de',
    'Italian': 'it', 'Russian': 'ru', 'Spanish': 'es',
}
LANG_COLORS = {
    'English': '#1f77b4', 'French': '#d62728', 'German': '#2ca02c',
    'Italian': '#ff7f0e', 'Russian': '#9467bd', 'Spanish': '#8c564b',
}


# ── FETCH (same cache as json_generator.ipynb and canon_ngram_analysis.py) ────
def fetch_ngram(query, corpus='en', start_year=1800, end_year=2019, smoothing=3):
    safe = query.replace(' ', '_').replace('/', '-')[:60]
    cache_path = os.path.join(CACHE_DIR, f'{safe}_{corpus}_{start_year}_{end_year}.json')
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            raw = json.load(f)
    else:
        r = requests.get(
            'https://books.google.com/ngrams/json',
            params={'content': query, 'year_start': start_year,
                    'year_end': end_year, 'corpus': corpus, 'smoothing': smoothing},
            timeout=15
        )
        r.raise_for_status()
        raw = r.json()
        with open(cache_path, 'w') as f:
            json.dump(raw, f)
        time.sleep(0.6)
    years = list(range(start_year, end_year + 1))
    df = pd.DataFrame({'year': years})
    if not raw:
        df['freq'] = 0.0
        return df.set_index('year')['freq']
    for item in raw:
        df[item['ngram']] = item['timeseries']
    col = [c for c in df.columns if c != 'year']
    if not col:
        df['freq'] = 0.0
        return df.set_index('year')['freq']
    s = df.set_index('year')[col[0]]
    s.name = query
    return s


# ── LOAD NOVELS LIST ──────────────────────────────────────────────────────────
df_novels = pd.read_csv('final_list_w_dates_genres.csv')
df_novels['original_publication_year'] = pd.to_numeric(
    df_novels['original_publication_year'], errors='coerce')
df_novels = df_novels.dropna(subset=['original_publication_year'])
df_novels['original_publication_year'] = df_novels['original_publication_year'].astype(int)
df_novels['query_title'] = df_novels['title'].str.title()


# ── BATCH FETCH — English corpus ──────────────────────────────────────────────
print("Loading English Ngram data (cached after first run)...")
all_series = {}
for i, row in df_novels.iterrows():
    title  = row['query_title']
    pub_yr = row['original_publication_year']
    start  = max(pub_yr - 5, 1800)
    all_series[title] = fetch_ngram(title, corpus='en', start_year=start, end_year=2019)
    print(f"  [{i+1:>3}/{len(df_novels)}] {title}")

print(f"Done. {len(all_series)} series.\n")


# # ─────────────────────────────────────────────────────────────────────────────
# # ANALYSIS A — Cultural immortality vs. decay
# #   Retention ratio = mean(2000–2019) / mean(peak decade)
# #   Ratio ≥ 1: still ascending or holding. Ratio → 0: fading.
# # ─────────────────────────────────────────────────────────────────────────────
# print("=" * 70)
# print("ANALYSIS A — Cultural immortality vs. decay")
# print("=" * 70)

# decay_records = []
# for _, row in df_novels.iterrows():
#     title  = row['query_title']
#     pub_yr = row['original_publication_year']
#     s      = all_series[title]
#     s_post = s[s.index >= pub_yr]
#     if s_post.empty or s_post.max() == 0:
#         continue

#     s_smooth  = s_post.rolling(10, center=True, min_periods=5).mean()
#     peak_year = int(s_smooth.idxmax())
#     peak_dec  = (peak_year // 10) * 10

#     mean_peak_dec = float(s[s.index.map(lambda y: (y // 10) * 10 == peak_dec)].mean())
#     mean_modern   = float(s[s.index >= 2000].mean())

#     if mean_peak_dec == 0:
#         continue

#     retention = mean_modern / mean_peak_dec

#     decay_records.append({
#         'title': title, 'pub_year': pub_yr,
#         'peak_year': peak_year, 'retention': retention,
#         'mean_modern': mean_modern,
#     })

# decay_df = pd.DataFrame(decay_records).sort_values('retention', ascending=False)
# print("\nTop 10 immortals (highest retention):")
# print(decay_df.head(10)[['title', 'pub_year', 'peak_year', 'retention']].to_string(index=False))
# print("\nTop 10 fading (lowest retention):")
# print(decay_df.tail(10)[['title', 'pub_year', 'peak_year', 'retention']].to_string(index=False))

# # Plot: show the 5 most immortal and 5 most faded trajectories
# fig, axes = plt.subplots(1, 2, figsize=(14, 5))
# for ax, group, label, color in [
#     (axes[0], decay_df.head(5), 'Most immortal', '#16a34a'),
#     (axes[1], decay_df.tail(5), 'Most faded',    '#dc2626'),
# ]:
#     for _, row in group.iterrows():
#         s = all_series[row['title']]
#         s_norm = s / s.max() if s.max() > 0 else s
#         ax.plot(s_norm.index, s_norm.values, alpha=0.8, linewidth=1.4,
#                 label=row['title'])
#     ax.axvspan(2000, 2019, color=color, alpha=0.08, label='Modern window')
#     ax.set_title(label)
#     ax.set_ylabel('Normalized frequency (0–1)')
#     ax.set_xlabel('Year')
#     ax.legend(fontsize=7, loc='upper left')
#     ax.set_xlim(1800, 2020)

# fig.suptitle('Cultural immortality vs. decay\n(retention = mean 2000–2019 / mean peak decade)',
#              fontsize=12)
# plt.tight_layout()
# plt.savefig('figures/analysisA_decay.png', dpi=150, bbox_inches='tight')
# plt.show()


# # ─────────────────────────────────────────────────────────────────────────────
# # ANALYSIS B — Rediscovery detection
# #   Revival score = mean(1990–2019) / mean(1930–1960), normalized to own peak.
# #   A trough followed by a modern revival = true rediscovery.
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n" + "=" * 70)
# print("ANALYSIS B — Rediscovery detection")
# print("=" * 70)

# revival_records = []
# for _, row in df_novels.iterrows():
#     title  = row['query_title']
#     pub_yr = row['original_publication_year']
#     s      = all_series[title]
#     if s.max() == 0:
#         continue

#     s_norm = s / s.max()   # 0–1 scale relative to own peak

#     early  = s_norm[(s_norm.index >= 1930) & (s_norm.index <= 1960)]
#     modern = s_norm[(s_norm.index >= 1990) & (s_norm.index <= 2019)]
#     trough = s_norm[(s_norm.index >= 1940) & (s_norm.index <= 1980)]

#     if early.empty or modern.empty or trough.empty:
#         continue

#     early_mean  = float(early.mean())
#     modern_mean = float(modern.mean())
#     trough_min  = float(trough.min())
#     revival_score = modern_mean / early_mean if early_mean > 0 else np.nan

#     revival_records.append({
#         'title': title, 'pub_year': pub_yr,
#         'early_mean': early_mean, 'modern_mean': modern_mean,
#         'trough_min': trough_min, 'revival_score': revival_score,
#     })

# revival_df = pd.DataFrame(revival_records).dropna().sort_values(
#     'revival_score', ascending=False)

# # True rediscoveries: had a notable trough AND modern revival > early period
# true_rediscoveries = revival_df[
#     (revival_df['trough_min'] < 0.35) &   # dipped low relative to own peak
#     (revival_df['revival_score'] > 1.5)    # modern period > 1.5× the mid-century level
# ].head(8)

# print(f"\n{len(true_rediscoveries)} true rediscoveries (trough < 35% of peak, then modern > 1.5× mid-century):")
# print(true_rediscoveries[['title', 'pub_year', 'trough_min',
#                            'early_mean', 'modern_mean', 'revival_score']].to_string(index=False))

# # Plot rediscovery trajectories
# fig, ax = plt.subplots(figsize=(12, 5))
# rng = np.random.default_rng(1)
# palette = plt.cm.tab10(np.linspace(0, 1, len(true_rediscoveries)))
# for (_, row), color in zip(true_rediscoveries.iterrows(), palette):
#     s = all_series[row['title']]
#     s_norm = s / s.max()
#     ax.plot(s_norm.index, s_norm.values, linewidth=1.6, color=color,
#             label=f"{row['title']} ({int(row['pub_year'])})")

# ax.axvspan(1930, 1960, color='#fde68a', alpha=0.3, label='Early window (1930–60)')
# ax.axvspan(1990, 2019, color='#bbf7d0', alpha=0.3, label='Modern window (1990–2019)')
# ax.set_ylabel('Normalized frequency (0–1)')
# ax.set_xlabel('Year')
# ax.set_title('Rediscovered classics — novels that went quiet then came back')
# ax.legend(fontsize=7.5, loc='upper left', ncol=2)
# ax.set_xlim(1850, 2020)
# plt.tight_layout()
# plt.savefig('figures/analysisB_rediscovery.png', dpi=150, bbox_inches='tight')
# plt.show()


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS C — Co-movement clustering
#   Pearson correlation of year-by-year Ngram frequencies (1900–2019).
#   Books that move together share cultural moment drivers.
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS C — Co-movement clustering")
print("=" * 70)

COMMON_START = 1900
COMMON_END   = 2019

matrix_data = {}
for _, row in df_novels.iterrows():
    if row['count'] < 3:
        continue
    title  = row['query_title']
    pub_yr = row['original_publication_year']
    s      = all_series[title]

    # Zero-fill pre-publication years within common window
    full_idx = pd.RangeIndex(COMMON_START, COMMON_END + 1)
    s_aligned = s.reindex(full_idx, fill_value=0.0)
    if pub_yr > COMMON_START:
        s_aligned.loc[COMMON_START:pub_yr - 1] = 0.0

    # Normalize to 0–1 so scale differences don't dominate correlation
    mx = s_aligned.max()
    if mx > 0:
        matrix_data[title] = s_aligned / mx

# Build correlation matrix
corr_df = pd.DataFrame(matrix_data).corr()
titles_ordered = corr_df.columns.tolist()

# Hierarchical clustering
dist = squareform(np.clip(1 - corr_df.values, 0, None))
Z = linkage(dist, method='ward')
_dend_result = dendrogram(Z, no_plot=True)
order = _dend_result['leaves']
corr_reordered = corr_df.iloc[order, order]

print(f"\nCorrelation matrix: {corr_df.shape[0]} × {corr_df.shape[1]} novels")
print(f"Mean pairwise correlation: {corr_df.values[np.triu_indices_from(corr_df.values, k=1)].mean():.3f}")

# Print the top strongly co-moving pairs
pairs = []
for i in range(len(titles_ordered)):
    for j in range(i + 1, len(titles_ordered)):
        pairs.append((titles_ordered[i], titles_ordered[j],
                      corr_df.iloc[i, j]))
pairs_df = pd.DataFrame(pairs, columns=['a', 'b', 'r']).sort_values('r', ascending=False)
print("\nTop 15 most co-moving pairs:")
print(pairs_df.head(15).to_string(index=False))
print("\nTop 15 most negatively correlated pairs:")
print(pairs_df.tail(15).sort_values('r').to_string(index=False))

def _fmt_pairs(subset, path, title):
    t = subset.copy()
    t['r'] = t['r'].map('{:.3f}'.format)
    t.columns = ['Novel A', 'Novel B', 'Pearson r']
    save_table_png(t, path, title=title)

_fmt_pairs(pairs_df.head(15),
           'figures/analysisC_top_pairs.png',
           'Top 15 most co-moving novel pairs (Pearson r, 1900–2019)')
_fmt_pairs(pairs_df.tail(15).sort_values('r'),
           'figures/analysisC_bottom_pairs.png',
           'Top 15 most negatively correlated novel pairs (Pearson r, 1900–2019)')

# Trajectory comparison plots for top/bottom 3 pairs
for group_label, pair_subset, suptitle, fname in [
    ('positive', pairs_df.head(3),                  'Top 3 most co-moving pairs',             'analysisC_pairs_positive'),
    ('negative', pairs_df.tail(3).sort_values('r'), 'Top 3 most negatively correlated pairs', 'analysisC_pairs_negative'),
]:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=False)
    for ax, (_, pair) in zip(axes, pair_subset.iterrows()):
        for title, color in [(pair['a'], '#2563eb'), (pair['b'], '#dc2626')]:
            s = all_series[title]
            mx = s.max()
            if mx > 0:
                s_norm = s / mx
                ax.plot(s_norm.index, s_norm.values, color=color, linewidth=1.4,
                        label=title, alpha=0.85)
        ax.set_title(f'r = {pair["r"]:.3f}', fontsize=9)
        ax.set_xlabel('Year')
        ax.set_ylabel('Normalized frequency')
        ax.set_xlim(1800, 2020)
        ax.legend(fontsize=7, loc='upper left')
    fig.suptitle(suptitle, fontsize=12)
    plt.tight_layout()
    plt.savefig(f'figures/{fname}.png', dpi=150, bbox_inches='tight')
    plt.show()

# Seaborn clustermap — dendrograms on both margins, easier to read cluster structure
cg = sns.clustermap(
    corr_df,
    method='ward', metric='euclidean',
    cmap='RdBu_r', vmin=-0.3, vmax=1,
    figsize=(16, 16),
    dendrogram_ratio=0.06,
    xticklabels=True, yticklabels=True,
    cbar_pos=None,
    cbar_kws={'label': 'Pearson r (year-by-year Ngram frequency)'},
    linewidths=0,
)
cg.ax_heatmap.set_xticklabels(
    cg.ax_heatmap.get_xticklabels(), rotation=90, fontsize=6)
cg.ax_heatmap.set_yticklabels(
    cg.ax_heatmap.get_yticklabels(), rotation=0,  fontsize=6)
cg.figure.suptitle(
    'Co-movement clustering of classic novels — clustermap\n'
    '(Pearson r of year-by-year English Ngram frequencies, 1900–2019)',
    fontsize=11, y=1.01)

# Add colorbar manually in the top-left corner, clear of the heatmap
cbar_ax = cg.figure.add_axes([0.01, 0.06, 0.015, 0.25])
import matplotlib as mpl
cg.figure.colorbar(
    mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=-0.3, vmax=1), cmap='RdBu_r'),
    cax=cbar_ax
)

cg.figure.savefig('figures/analysisC_clustermap.png', dpi=150, bbox_inches='tight')
plt.show()


# ── EXPORT JSON FOR WEBSITE ───────────────────────────────────────────────────
os.makedirs('articles/data/analysis-c', exist_ok=True)

# Recompute linkage exactly as seaborn does: Ward + Euclidean on correlation vectors
_Z_sns = linkage(corr_df.values, method='ward', metric='euclidean')
_dend_sns = dendrogram(_Z_sns, no_plot=True)
_sns_order = _dend_sns['leaves']
_corr_sns = corr_df.iloc[_sns_order, _sns_order]

_max_depth_sns = float(max(max(d) for d in _dend_sns['dcoord']))
clustermap_json = {
    'titles': _corr_sns.columns.tolist(),
    'matrix': [[round(v, 4) for v in row] for row in _corr_sns.values.tolist()],
    'dendrogram': {
        'icoord':    _dend_sns['icoord'],
        'dcoord':    _dend_sns['dcoord'],
        'max_depth': _max_depth_sns,
        'n':         len(_dend_sns['leaves']),
    },
}
with open('articles/data/analysis-c/clustermap.json', 'w') as f:
    json.dump(clustermap_json, f)
print("Saved → articles/data/analysis-c/clustermap.json")

# Cluster trajectory JSONs (clusters 0, 2, 3) — use same seaborn linkage
N_CLUSTERS = 4
cluster_labels = fcluster(_Z_sns, t=N_CLUSTERS, criterion='maxclust') - 1  # 0-indexed
title_to_cluster = {title: int(cluster_labels[i])
                    for i, title in enumerate(corr_df.columns)}

TRAJ_YEARS = list(range(COMMON_START, COMMON_END + 1))

for target_cluster in [0, 2, 3]:
    members = [t for t, c in title_to_cluster.items() if c == target_cluster]
    if not members:
        print(f"Cluster {target_cluster}: no members, skipping")
        continue
    series = {}
    for title in members:
        s = all_series[title]
        s_aligned = s.reindex(pd.RangeIndex(COMMON_START, COMMON_END + 1), fill_value=0.0)
        mx = float(s_aligned.max())
        s_norm = s_aligned / mx if mx > 0 else s_aligned
        series[title] = [round(float(v), 6) for v in s_norm.values]
    cluster_json = {
        'years': TRAJ_YEARS,
        'series': series,
        'events': {},
    }
    path = f'articles/data/analysis-c/cluster_{target_cluster}.json'
    with open(path, 'w') as f:
        json.dump(cluster_json, f)
    print(f"Saved → {path}  ({len(members)} novels)")

# Pairs trajectory JSONs — top 3 and bottom 3 correlated pairs
for fname, pair_subset in [
    ('pairs_positive', pairs_df.head(3)),
    ('pairs_negative', pairs_df.tail(3).sort_values('r')),
]:
    involved = list(set(pair_subset['a'].tolist() + pair_subset['b'].tolist()))
    series = {}
    for title in involved:
        s = all_series[title]
        s_aligned = s.reindex(pd.RangeIndex(COMMON_START, COMMON_END + 1), fill_value=0.0)
        mx = float(s_aligned.max())
        s_norm = s_aligned / mx if mx > 0 else s_aligned
        series[title] = [round(float(v), 6) for v in s_norm.values]
    pairs_json = {
        'years': TRAJ_YEARS,
        'pairs': [{'a': row['a'], 'b': row['b'], 'r': round(float(row['r']), 4)}
                  for _, row in pair_subset.iterrows()],
        'series': series,
    }
    path = f'articles/data/analysis-c/{fname}.json'
    with open(path, 'w') as f:
        json.dump(pairs_json, f)
    print(f"Saved → {path}")


# # ─────────────────────────────────────────────────────────────────────────────
# # ANALYSIS D — Book of each decade
# #   For each decade, which novel had the highest frequency relative to its
# #   own long-run mean? Excludes the publication decade and decade after.
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n" + "=" * 70)
# print("ANALYSIS D — Book of each decade")
# print("=" * 70)

# DECADES = list(range(1820, 2020, 10))
# decade_winners = []

# for dec in DECADES:
#     best_title, best_ratio = None, -np.inf
#     for _, row in df_novels.iterrows():
#         title  = row['query_title']
#         pub_yr = row['original_publication_year']
#         if pub_yr > dec - 10:   # must be published at least a decade earlier
#             continue
#         s = all_series[title]
#         decade_vals = s[(s.index >= dec) & (s.index < dec + 10)]
#         overall     = s[s.index >= pub_yr]
#         if decade_vals.empty or overall.empty or overall.mean() == 0:
#             continue
#         ratio = decade_vals.mean() / overall.mean()
#         if ratio > best_ratio:
#             best_ratio, best_title = ratio, title
#     if best_title:
#         decade_winners.append({'decade': dec, 'title': best_title,
#                                 'relative_spike': best_ratio})
#         print(f"  {dec}s → {best_title}  (relative spike: {best_ratio:.2f}×)")

# winners_df = pd.DataFrame(decade_winners)

# fig, ax = plt.subplots(figsize=(13, 5))
# bars = ax.barh(
#     [f"{d}s" for d in winners_df['decade']],
#     winners_df['relative_spike'],
#     color='#3b82f6', alpha=0.75, height=0.6
# )
# for bar, row in zip(bars, winners_df.itertuples()):
#     ax.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height() / 2,
#             row.title, va='center', fontsize=7.5, color='#1f2937')
# ax.set_xlabel('Relative spike (decade mean / novel long-run mean)')
# ax.set_title('Book of each decade\n'
#              '(which novel was most culturally salient relative to its own baseline?)')
# ax.invert_yaxis()
# plt.tight_layout()
# plt.savefig('figures/analysisD_decade_winner.png', dpi=150, bbox_inches='tight')
# plt.show()


# # ─────────────────────────────────────────────────────────────────────────────
# # ANALYSIS E — War and crisis effect
# #   Average normalized Ngram across all novels, overlaid with major crises.
# #   Permutation test: are crisis-year means significantly above baseline?
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n" + "=" * 70)
# print("ANALYSIS E — War and crisis effect")
# print("=" * 70)

# CRISIS_WINDOWS = {
#     'WWI\n1914–18':         (1914, 1918),
#     'WWII\n1939–45':        (1939, 1945),
#     'Cold War\npeak 55–65': (1955, 1965),
#     '1968\nunrest':         (1966, 1972),
#     '2008\ncrisis':         (2008, 2012),
# }

# # Build aggregate: for each year, mean of normalized (per-novel) frequencies
# # Only include novels published before that year
# agg_years = range(1850, 2020)
# agg_vals  = []

# for yr in agg_years:
#     vals = []
#     for _, row in df_novels.iterrows():
#         title  = row['query_title']
#         pub_yr = row['original_publication_year']
#         if pub_yr >= yr:
#             continue
#         s = all_series[title]
#         if yr not in s.index:
#             continue
#         mx = s.max()
#         if mx > 0:
#             vals.append(float(s[yr]) / mx)
#     agg_vals.append(np.mean(vals) if vals else np.nan)

# agg = pd.Series(agg_vals, index=list(agg_years)).dropna()
# agg_smooth = agg.rolling(5, center=True, min_periods=3).mean()

# # Classify each year: crisis or baseline
# crisis_years = set()
# for start, end in CRISIS_WINDOWS.values():
#     crisis_years.update(range(start, end + 1))

# crisis_vals   = agg[agg.index.isin(crisis_years)].dropna()
# baseline_vals = agg[~agg.index.isin(crisis_years)].dropna()
# t_stat, t_p   = stats.ttest_ind(crisis_vals, baseline_vals)

# print(f"\nCrisis years mean:   {crisis_vals.mean():.4f}")
# print(f"Baseline years mean: {baseline_vals.mean():.4f}")
# print(f"t-test: t={t_stat:.3f}  p={t_p:.4f}")

# fig, ax = plt.subplots(figsize=(14, 5))
# ax.plot(agg.index, agg_smooth.values, color='#1d4ed8', linewidth=1.5,
#         label='Aggregate (5-yr smooth)')
# ax.fill_between(agg.index, agg_smooth.values, alpha=0.12, color='#1d4ed8')

# for label, (start, end) in CRISIS_WINDOWS.items():
#     ax.axvspan(start, end, color='#fca5a5', alpha=0.35)
#     ax.text((start + end) / 2, ax.get_ylim()[1] * 0.97, label,
#             ha='center', va='top', fontsize=7.5, color='#991b1b')

# ax.set_xlabel('Year')
# ax.set_ylabel('Mean normalized frequency across all novels')
# ax.set_title(f'Do people turn to the classics during crises?\n'
#              f'Crisis years vs. baseline: t={t_stat:.2f}  p={t_p:.3f}')
# ax.legend()
# plt.tight_layout()
# plt.savefig('figures/analysisE_crisis.png', dpi=150, bbox_inches='tight')
# plt.show()


# # ─────────────────────────────────────────────────────────────────────────────
# # ANALYSIS F — Cross-language divergence
# #   Fetch all 6 corpora using the English title.
# #   For each novel, compute pairwise Pearson r between language curves (1900–2019).
# #   Low mean r = discourse driven by language-specific events.
# #   High mean r = global cultural events drive the discussion.
# # ─────────────────────────────────────────────────────────────────────────────
# print("\n" + "=" * 70)
# print("ANALYSIS F — Cross-language divergence")
# print("(fetching 6 corpora × 118 novels — uses cache after first run)")
# print("=" * 70)

# lang_series_all = {}   # {title: {lang: Series}}

# for i, row in df_novels.iterrows():
#     title  = row['query_title']
#     pub_yr = row['original_publication_year']
#     start  = max(pub_yr - 5, 1900)   # Ngram pre-1900 is sparse
#     lang_data = {}
#     for lang, corpus in LANGUAGES.items():
#         s = fetch_ngram(title, corpus=corpus, start_year=start, end_year=2019)
#         lang_data[lang] = s
#     lang_series_all[title] = lang_data
#     print(f"  [{i+1:>3}/{len(df_novels)}] {title}")

# print("Multi-language fetch complete.\n")

# # Compute metrics per novel
# lang_records = []
# for _, row in df_novels.iterrows():
#     title   = row['query_title']
#     pub_yr  = row['original_publication_year']
#     lang_data = lang_series_all[title]

#     # Normalize each language series to 0–1
#     normed = {}
#     for lang, s in lang_data.items():
#         mx = s.max()
#         if mx > 0:
#             normed[lang] = s / mx

#     if len(normed) < 2:
#         continue

#     # Align to common window: publication year to 2019
#     common_start = max(pub_yr, 1900)
#     common_idx   = range(common_start, 2020)
#     aligned = {}
#     for lang, s in normed.items():
#         s_aligned = s.reindex(common_idx, fill_value=0.0)
#         if s_aligned.sum() > 0:
#             aligned[lang] = s_aligned

#     if len(aligned) < 2:
#         continue

#     # Pairwise Pearson r
#     langs = list(aligned.keys())
#     rs = []
#     for i in range(len(langs)):
#         for j in range(i + 1, len(langs)):
#             r, _ = stats.pearsonr(aligned[langs[i]].values,
#                                   aligned[langs[j]].values)
#             rs.append(r)

#     # Spread: number of languages with peak > 0.05 (non-trivial signal)
#     spread = sum(1 for s in normed.values() if s.max() >= 0.05)

#     lang_records.append({
#         'title': title, 'pub_year': pub_yr,
#         'mean_cross_r': np.mean(rs),
#         'spread': spread,
#         'langs_with_signal': [l for l, s in normed.items() if s.max() >= 0.05],
#     })

# lang_df = pd.DataFrame(lang_records).sort_values('mean_cross_r', ascending=False)
# print("Most globally coherent (high cross-language correlation):")
# print(lang_df.head(10)[['title', 'pub_year', 'mean_cross_r', 'spread']].to_string(index=False))
# print("\nMost language-specific (low cross-language correlation):")
# print(lang_df.tail(10)[['title', 'pub_year', 'mean_cross_r', 'spread']].to_string(index=False))

# def _fmt_lang_df(subset, label):
#     t = subset[['title', 'pub_year', 'mean_cross_r', 'spread']].copy()
#     t['mean_cross_r'] = t['mean_cross_r'].map('{:.3f}'.format)
#     t.columns = ['Title', 'Pub. year', 'Mean cross-lang r', 'Languages w/ signal']
#     save_table_png(t, f'figures/analysisF_{label}.png',
#                    title={'coherent': 'Most globally coherent — high cross-language correlation',
#                           'specific':  'Most language-specific — low cross-language correlation'}[label])

# _fmt_lang_df(lang_df.head(10), 'coherent')
# _fmt_lang_df(lang_df.tail(10), 'specific')

# # Trajectory comparison: top/bottom 3 by cross-language coherence
# for group_label, novel_subset, suptitle, fname in [
#     ('coherent', lang_df.head(3),                       'Top 3 most globally coherent novels (all languages)',    'analysisF_traj_coherent'),
#     ('specific', lang_df.tail(3).sort_values('mean_cross_r'), 'Top 3 most language-specific novels (all languages)', 'analysisF_traj_specific'),
# ]:
#     fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=False)
#     for ax, (_, novel) in zip(axes, novel_subset.iterrows()):
#         title = novel['title']
#         for lang, color in LANG_COLORS.items():
#             s = lang_series_all[title][lang]
#             mx = s.max()
#             if mx > 0:
#                 s_norm = s / mx
#                 ax.plot(s_norm.index, s_norm.values, color=color, linewidth=1.3,
#                         label=lang, alpha=0.85)
#         ax.set_title(f'{title}\n(mean r = {novel["mean_cross_r"]:.3f})', fontsize=8.5)
#         ax.set_xlabel('Year')
#         ax.set_ylabel('Normalized frequency')
#         ax.legend(fontsize=6.5, loc='upper left')
#     fig.suptitle(suptitle, fontsize=12)
#     plt.tight_layout()
#     plt.savefig(f'figures/{fname}.png', dpi=150, bbox_inches='tight')
#     plt.show()

# # Heatmap: novels (rows) × languages (cols), normalized peak frequency
# heatmap_rows = []
# heatmap_titles = []
# for _, row in lang_df.sort_values('spread', ascending=False).head(40).iterrows():
#     title = row['title']
#     peaks = {}
#     for lang, s in lang_series_all[title].items():
#         peaks[lang] = s.max()
#     total = sum(peaks.values())
#     if total == 0:
#         continue
#     heatmap_rows.append({lang: peaks[lang] / total for lang in LANGUAGES})
#     heatmap_titles.append(title)

# heatmap_df = pd.DataFrame(heatmap_rows, index=heatmap_titles)

# fig, ax = plt.subplots(figsize=(9, 12))
# im = ax.imshow(heatmap_df.values, cmap='YlOrRd', aspect='auto', vmin=0)
# plt.colorbar(im, ax=ax, label='Share of total peak frequency across all languages')
# ax.set_xticks(range(len(LANGUAGES)))
# ax.set_xticklabels(list(LANGUAGES.keys()), fontsize=9)
# ax.set_yticks(range(len(heatmap_titles)))
# ax.set_yticklabels(heatmap_titles, fontsize=7)
# ax.set_title('Cross-language spread — top 40 novels by language breadth\n'
#              '(share of each novel\'s total Ngram peak per language corpus)', fontsize=10)
# plt.tight_layout()
# plt.savefig('figures/analysisF_language_spread.png', dpi=150, bbox_inches='tight')
# plt.show()

# print("\nDone. All figures saved to figures/")
