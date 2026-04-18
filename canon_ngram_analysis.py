import ast
import os
import json
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import requests
from scipy import stats
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

plt.rcParams['figure.dpi'] = 110
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

CACHE_DIR = 'data'
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs('figures', exist_ok=True)


# ── NGRAM FETCH (mirrors json_generator.ipynb, uses same cache) ───────────────
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

SKIP = {'Classics', 'Classic Literature', 'Fiction', 'Novels', 'Literature',
        'Adult', 'Read For School', 'School'}

def parse_genres(val):
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []

df_novels['genre_list'] = df_novels['genres'].apply(parse_genres)
df_novels['genre_count'] = df_novels['genre_list'].apply(
    lambda g: len([x for x in g if x not in SKIP]))
df_novels['query_title'] = df_novels['title'].str.title()


# ── BATCH FETCH ────────────────────────────────────────────────────────────────
print("Fetching Ngram data for all novels (cached after first run)...")
all_series = {}
for i, row in df_novels.iterrows():
    title  = row['query_title']
    pub_yr = row['original_publication_year']
    start  = max(pub_yr - 5, 1800)
    s = fetch_ngram(title, corpus='en', start_year=start, end_year=2019)
    all_series[title] = s
    print(f"  [{i+1:>3}/{len(df_novels)}] {title} ({pub_yr})  peak={s.max():.5f}")

print(f"\nFetch complete. {len(all_series)} series loaded.\n")


# ── FEATURE EXTRACTION ────────────────────────────────────────────────────────
records = []
for _, row in df_novels.iterrows():
    title   = row['query_title']
    pub_yr  = row['original_publication_year']
    s       = all_series[title]
    s_post  = s[s.index >= pub_yr]

    if s_post.empty or s_post.max() == 0:
        records.append({
            'title': title, 'count': row['count'], 'pub_year': pub_yr,
            'genre_count': row['genre_count'],
            'peak_freq': 0, 'lag_to_peak': np.nan,
            'longevity': 0, 'trajectory': np.nan, 'current_level': 0,
        })
        continue

    # Smooth with a 10-year rolling mean before peak detection so a single
    # noisy spike doesn't misplace the peak year. min_periods=5 handles
    # series edges without producing NaN for the whole early window.
    s_smooth = s_post.rolling(window=10, center=True, min_periods=5).mean()

    peak_freq   = s_smooth.max()
    peak_year   = s_smooth.idxmax()
    lag_to_peak = peak_year - pub_yr

    # Longevity: fraction of post-publication years where freq > 10 % of peak
    longevity = (s_post > peak_freq * 0.10).sum() / len(s_post)

    # Current level: mean frequency 2010–2019
    current_level = float(s[s.index >= 2010].mean()) if s.index.max() >= 2010 else 0.0

    # Trajectory: OLS slope over 1990–2019, normalized by mean (relative rate of change)
    s_recent = s[s.index >= 1990]
    if len(s_recent) >= 5 and s_recent.mean() > 0:
        slope, *_ = stats.linregress(s_recent.index, s_recent.values)
        trajectory = slope / s_recent.mean()
    else:
        trajectory = np.nan

    records.append({
        'title': title, 'count': row['count'], 'pub_year': pub_yr,
        'genre_count': row['genre_count'],
        'peak_freq': peak_freq, 'lag_to_peak': lag_to_peak,
        'longevity': longevity, 'trajectory': trajectory,
        'current_level': current_level,
    })

feat = pd.DataFrame(records)
feat_clean = feat.dropna()
print(f"Feature matrix: {feat.shape[0]} novels total, {feat_clean.shape[0]} with complete data\n")
print(feat_clean.describe().to_string())
print()


""" # ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1 — What predicts canonicity? (Multiple OLS Regression)
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("ANALYSIS 1 — Multiple Regression: what predicts canonicity score?")
print("=" * 70)

model = smf.ols(
    'count ~ peak_freq + lag_to_peak + longevity + genre_count + pub_year',
    data=feat_clean
).fit()
print(model.summary())

# Coefficient plot
fig, ax = plt.subplots(figsize=(8, 4))
coef   = model.params.drop('Intercept')
ci     = model.conf_int().drop('Intercept')
colors = ['#ef4444' if p < 0.05 else '#94a3b8'
          for p in model.pvalues.drop('Intercept')]

y_pos = range(len(coef))
ax.barh(list(y_pos), coef.values, xerr=[
    coef.values - ci[0].values,
    ci[1].values - coef.values
], color=colors, height=0.5, capsize=4, error_kw={'linewidth': 1.2})
ax.axvline(0, color='black', linewidth=0.8)
ax.set_yticks(list(y_pos))
ax.set_yticklabels([
    'Peak frequency', 'Lag to peak', 'Longevity',
    'Genre count', 'Publication year'
])
ax.set_xlabel('Regression coefficient (95 % CI)')
ax.set_title(f'What predicts canonicity score?\n'
             f'OLS  n={int(model.nobs)}  R²={model.rsquared:.3f}  '
             f'adj-R²={model.rsquared_adj:.3f}')
red_patch  = plt.Rectangle((0, 0), 1, 1, fc='#ef4444')
grey_patch = plt.Rectangle((0, 0), 1, 1, fc='#94a3b8')
ax.legend([red_patch, grey_patch], ['p < 0.05', 'p ≥ 0.05'], loc='lower right')
plt.tight_layout()
plt.savefig('figures/analysis1_regression.png', dpi=150, bbox_inches='tight')
plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2 — Slow burn vs. immediate classic
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2 — Slow burn vs. immediate classic (lag to peak)")
print("=" * 70)

a2 = feat_clean[feat_clean['lag_to_peak'] <= 200].copy()
r, p = stats.spearmanr(a2['lag_to_peak'], a2['count'])
print(f"Spearman r = {r:.3f}  p = {p:.4f}  n = {len(a2)}")

# Box plot: one box per canonicity score (1–6), showing lag distribution.
# Individual points are overlaid with horizontal jitter only (Y is fixed/discrete).
rng = np.random.default_rng(42)
fig, ax = plt.subplots(figsize=(9, 5))

score_levels = sorted(a2['count'].unique())
bp_data = [a2[a2['count'] == k]['lag_to_peak'].values for k in score_levels]

bp = ax.boxplot(bp_data, positions=score_levels, widths=0.5,
                patch_artist=True, showfliers=False,
                boxprops=dict(facecolor='#bfdbfe', alpha=0.7),
                medianprops=dict(color='#1d4ed8', linewidth=2),
                whiskerprops=dict(color='#6b7280'),
                capprops=dict(color='#6b7280'))

for k, vals in zip(score_levels, bp_data):
    jitter_x = rng.uniform(-0.18, 0.18, len(vals))
    ax.scatter(np.full(len(vals), k) + jitter_x, vals,
               s=30, color='#1d4ed8', alpha=0.55, linewidths=0, zorder=3)

# Annotate notable slow-burn high-scorers
for _, row in a2[(a2['lag_to_peak'] > 80) & (a2['count'] >= 4)].iterrows():
    ax.annotate(row['title'],
                xy=(row['count'], row['lag_to_peak']),
                xytext=(row['count'] + 0.25, row['lag_to_peak']),
                fontsize=6.5, color='#374151', va='center')

ax.set_xlabel('Canonicity score (number of lists)')
ax.set_ylabel('Years from publication to Ngram peak')
ax.set_title(f'Do slow burns become deeper classics?\n'
             f'Spearman r={r:.2f}  p={p:.3f}  n={len(a2)}')
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig('figures/analysis2_slowburn.png', dpi=150, bbox_inches='tight')
plt.show()

# Split into "immediate" (lag ≤ 30) vs "slow burn" (lag > 30)
immediate  = a2[a2['lag_to_peak'] <= 30]['count']
slow_burn  = a2[a2['lag_to_peak'] >  30]['count']
t_stat, t_p = stats.mannwhitneyu(immediate, slow_burn, alternative='two-sided')
print(f"\nImmediate classics (lag ≤ 30y): n={len(immediate)}, median count={immediate.median():.1f}")
print(f"Slow burns         (lag > 30y): n={len(slow_burn)}, median count={slow_burn.median():.1f}")
print(f"Mann-Whitney U={t_stat:.0f}  p={t_p:.4f}")
 """

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 5 — Trajectory clustering (novels up to 1950, first 50 years)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 5 — Ngram trajectory clustering (novels up to 1950)")
print("=" * 70)

PUB_CUTOFF  = 1950
WINDOW      = 50   # years after publication
N_CLUSTERS  = 4

# Grid is 0..50 — one point per year, 0 = publication year
year_offsets = np.arange(0, WINDOW + 1, dtype=float)  # 51 points

matrix_rows = []
meta_rows   = []
for _, row in feat_clean.iterrows():
    pub_yr = int(row['pub_year'])
    if pub_yr > PUB_CUTOFF:
        continue
    title  = row['title']
    s      = all_series[title]
    # Slice exactly pub_yr to pub_yr+50; require at least 40 years of data
    s_win  = s[(s.index >= pub_yr) & (s.index <= pub_yr + WINDOW)]
    if len(s_win) < 40 or s_win.max() == 0:
        continue
    # Interpolate onto the fixed 0–50 offset grid (handles any small gaps)
    offsets_avail = (s_win.index - pub_yr).astype(float)
    values = np.interp(year_offsets, offsets_avail, s_win.values)
    mx = values.max()
    if mx == 0:
        continue
    values /= mx   # normalize to 0–1 so clustering is shape-only
    matrix_rows.append(values)
    meta_rows.append({'title': title, 'count': row['count'],
                      'pub_year': pub_yr, 'peak_freq': row['peak_freq']})

X = np.array(matrix_rows)
meta_df = pd.DataFrame(meta_rows)
print(f"\n{len(meta_df)} novels published up to {PUB_CUTOFF} with ≥40 years of data.")

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=20)
meta_df['cluster'] = kmeans.fit_predict(X_scaled)

CLUSTER_COLORS = ['#2563eb', '#16a34a', '#dc2626', '#d97706']

# Print cluster summaries
print(f"\n{N_CLUSTERS} clusters (KMeans on first-{WINDOW}-year trajectories):\n")
for k in range(N_CLUSTERS):
    grp = meta_df[meta_df['cluster'] == k]
    print(f"Cluster {k}  (n={len(grp)}, median count={grp['count'].median():.1f}, "
          f"median peak={grp['peak_freq'].median():.5f})")
    print("  ", ", ".join(grp.sort_values('count', ascending=False)['title'].head(8).tolist()))

# Plot mean trajectory per cluster + individual faint lines
fig, axes = plt.subplots(2, 2, figsize=(14, 7), sharey=False)
axes = axes.flatten()

for k, ax in enumerate(axes):
    cluster_mask = meta_df['cluster'] == k
    for idx in np.where(cluster_mask)[0]:
        ax.plot(year_offsets, X[idx], color=CLUSTER_COLORS[k], alpha=0.12, linewidth=0.8)
    mean_curve = X[cluster_mask].mean(axis=0)
    ax.plot(year_offsets, mean_curve, color=CLUSTER_COLORS[k], linewidth=2.5, label='Mean')
    n_k     = cluster_mask.sum()
    med_cnt = meta_df.loc[cluster_mask, 'count'].median()
    ax.set_title(f'Cluster {k}  (n={n_k}, median canonicity={med_cnt:.0f})', fontsize=10)
    ax.set_xlabel('Years after publication')
    ax.set_ylabel('Normalized frequency')
    ax.set_ylim(0, 1.1)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(10))

fig.suptitle(f'Ngram trajectory clusters — first {WINDOW} years after publication (novels up to {PUB_CUTOFF})',
             fontsize=12, y=1.01)
plt.tight_layout()
plt.savefig('figures/analysis5_clusters.png', dpi=150, bbox_inches='tight')
plt.show()

# Canonicity score distribution by cluster (box plot)
fig, ax = plt.subplots(figsize=(8, 4))
for k in range(N_CLUSTERS):
    grp = meta_df[meta_df['cluster'] == k]['count']
    ax.boxplot(grp, positions=[k], widths=0.5,
               patch_artist=True,
               boxprops=dict(facecolor=CLUSTER_COLORS[k], alpha=0.6),
               medianprops=dict(color='black', linewidth=2))
ax.set_xticks(range(N_CLUSTERS))
ax.set_xticklabels([f'Cluster {k}' for k in range(N_CLUSTERS)])
ax.set_ylabel('Canonicity score (# of lists)')
ax.set_title('Do certain trajectory shapes produce deeper classics?\nCanonicity score by Ngram trajectory cluster')
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig('figures/analysis5_cluster_counts.png', dpi=150, bbox_inches='tight')
plt.show()

# Kruskal-Wallis test across clusters
groups = [meta_df[meta_df['cluster'] == k]['count'].values for k in range(N_CLUSTERS)]
kw_stat, kw_p = stats.kruskal(*groups)
print(f"\nKruskal-Wallis across clusters: H={kw_stat:.3f}  p={kw_p:.4f}")

# ── EXPORT JSON FOR WEBSITE ───────────────────────────────────────────────────
os.makedirs('articles/data/analysis-5', exist_ok=True)

for k in range(N_CLUSTERS):
    cluster_mask = meta_df['cluster'] == k
    row_indices  = np.where(cluster_mask)[0]
    titles       = meta_df.loc[cluster_mask, 'title'].tolist()

    series = {}
    for i, title in zip(row_indices, titles):
        series[title] = [round(float(v), 6) for v in X[i]]

    cluster_json = {
        'years':  list(range(WINDOW + 1)),  # 0–50 (years after publication)
        'series': series,
        'events': {},
    }
    path = f'articles/data/analysis-5/cluster_{k}.json'
    with open(path, 'w') as f:
        json.dump(cluster_json, f)
    print(f"Saved → {path}  ({len(titles)} novels)")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 6 — Anniversary effect
# ═══════════════════════════════════════════════════════════════════════════════
""" print("\n" + "=" * 70)
print("ANALYSIS 6 — Anniversary effect (50 / 100 / 150 / 200 year spikes)")
print("=" * 70)

ANNIVERSARIES = [50, 100, 150, 200]
WINDOW = 7   # compare anniversary year to ±7 year window (excluding the year itself)

anniv_records = []
for _, row in feat_clean.iterrows():
    title  = row['title']
    pub_yr = int(row['pub_year'])
    s      = all_series[title]

    for gap in ANNIVERSARIES:
        anniv_yr = pub_yr + gap
        if anniv_yr < 1800 or anniv_yr > 2019:
            continue
        if anniv_yr not in s.index:
            continue

        anniv_val = float(s[anniv_yr])

        # Baseline: mean of the window excluding the anniversary year itself
        window_yrs = [y for y in range(anniv_yr - WINDOW, anniv_yr + WINDOW + 1)
                      if y != anniv_yr and y in s.index]
        if len(window_yrs) < 4:
            continue
        baseline = s[window_yrs]
        base_mean = float(baseline.mean())
        base_std  = float(baseline.std())

        z_score = (anniv_val - base_mean) / base_std if base_std > 0 else 0.0
        relative_lift = (anniv_val - base_mean) / base_mean if base_mean > 0 else 0.0

        anniv_records.append({
            'title': title, 'count': row['count'],
            'pub_year': pub_yr, 'anniversary': gap,
            'anniv_year': anniv_yr,
            'anniv_val': anniv_val,
            'base_mean': base_mean,
            'z_score': z_score,
            'relative_lift': relative_lift,
        })

anniv_df = pd.DataFrame(anniv_records)
print(f"\n{len(anniv_df)} anniversary data points across {anniv_df['title'].nunique()} novels\n")

# Summary: mean z-score per anniversary milestone
print("Mean z-score at each anniversary (positive = spike above local baseline):")
summary = anniv_df.groupby('anniversary')['z_score'].agg(['mean', 'median', 'count'])
print(summary.to_string())

# One-sample t-test: is the mean z-score significantly > 0 at each anniversary?
print()
for gap in ANNIVERSARIES:
    grp = anniv_df[anniv_df['anniversary'] == gap]['z_score'].dropna()
    if len(grp) < 5:
        continue
    t, p = stats.ttest_1samp(grp, 0)
    sig = "**" if p < 0.01 else ("*" if p < 0.05 else "ns")
    print(f"  {gap}-year anniversary: mean z={grp.mean():.3f}  "
          f"t={t:.2f}  p={p:.4f}  {sig}  n={len(grp)}")

# Bar chart: mean z-score per anniversary
fig, ax = plt.subplots(figsize=(8, 4))
gap_means = anniv_df.groupby('anniversary')['z_score'].mean()
gap_sems  = anniv_df.groupby('anniversary')['z_score'].sem()
gap_ns    = anniv_df.groupby('anniversary')['z_score'].count()

bars = ax.bar(
    [f"{g}-year" for g in gap_means.index],
    gap_means.values,
    yerr=gap_sems.values,
    color=['#2563eb' if v > 0 else '#ef4444' for v in gap_means.values],
    alpha=0.8, capsize=5, error_kw={'linewidth': 1.2}, width=0.5
)
ax.bar_label(bars, labels=[f'n={n}' for n in gap_ns.values],
             padding=6, fontsize=8, color='#6b7280')
ax.axhline(0, color='black', linewidth=0.8)
ax.set_ylabel('Mean z-score vs. local ±7-year baseline')
ax.set_title('Do classic novels spike on round anniversaries?\nMean Ngram z-score at 50/100/150/200-year milestones')
plt.tight_layout()
plt.savefig('figures/analysis6_anniversary.png', dpi=150, bbox_inches='tight')
plt.show()

# Top anniversary spikes (most dramatic single cases)
print("\nTop 15 individual anniversary spikes (by z-score):")
print(anniv_df.nlargest(15, 'z_score')[
    ['title', 'pub_year', 'anniversary', 'anniv_year', 'z_score', 'relative_lift']
].to_string(index=False))

print("\nDone. Figures saved to figures/")
 """