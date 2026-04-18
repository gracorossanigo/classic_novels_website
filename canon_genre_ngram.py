import ast
import os
import json
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

plt.rcParams['figure.dpi'] = 110
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

CACHE_DIR = 'data'
os.makedirs('figures', exist_ok=True)

SKIP = {'Classics', 'Classic Literature', 'Fiction', 'Novels', 'Literature',
        'Adult', 'Read For School', 'School', 'Russian', 'Russian Literature',
          'American', 'Historical', '19th Century', '20th Century',
            "British Literature", 'Audiobook', 'Victorian', 'France',
              'Middle Grade', 'Russia', 'Russian Literature', 'Philosophy', 'Feminism',
              'High School', 'African American', 'Young Adult'}

MIN_NOVELS_PER_GENRE = 6   # genres with fewer novels get too noisy
EARLY_WINDOW         = 35
LIFECYCLE_WINDOW     = 150  # how many years to show in the genre lifecycle plot
REAL_START           = 1900
REAL_END             = 2019


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
    return df.set_index('year')[col[0]]


# ── LOAD ──────────────────────────────────────────────────────────────────────
df_novels = pd.read_csv('final_list_w_dates_genres.csv')
df_novels['original_publication_year'] = pd.to_numeric(
    df_novels['original_publication_year'], errors='coerce')
df_novels = df_novels.dropna(subset=['original_publication_year'])
df_novels['original_publication_year'] = df_novels['original_publication_year'].astype(int)
df_novels['query_title'] = df_novels['title'].str.title()

def parse_genres(val):
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return []

df_novels['genre_list'] = df_novels['genres'].apply(parse_genres)
df_novels['genre_list'] = df_novels['genre_list'].apply(
    lambda gs: [g for g in gs if g not in SKIP])

# ── BATCH FETCH ────────────────────────────────────────────────────────────────
print("Loading English Ngram data (from cache)...")
all_series = {}
for _, row in df_novels.iterrows():
    title  = row['query_title']
    pub_yr = row['original_publication_year']
    all_series[title] = fetch_ngram(
        title, corpus='en', start_year=max(pub_yr - 5, 1800), end_year=2019)
print(f"Done. {len(all_series)} series.\n")

# ── IDENTIFY TOP GENRES ────────────────────────────────────────────────────────
from collections import Counter
genre_counts = Counter(g for gs in df_novels['genre_list'] for g in gs)
top_genres = [g for g, n in genre_counts.most_common() if n >= MIN_NOVELS_PER_GENRE]
print(f"Genres with ≥{MIN_NOVELS_PER_GENRE} novels: {top_genres}\n")

palette = plt.cm.tab20(np.linspace(0, 1, len(top_genres)))
genre_color = {g: palette[i] for i, g in enumerate(top_genres)}


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1 — Genre lifecycle curves (0–LIFECYCLE_WINDOW years after publication)
# Each novel normalized by own all-time max, then averaged within genre.
# NaN-filled beyond each novel's available data, so the average thins out
# naturally at longer ages as fewer novels have that much history.
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print(f"ANALYSIS 1 — Genre lifecycle curves (first {LIFECYCLE_WINDOW} years)")
print("=" * 70)

genre_lifecycle = {}

for genre in top_genres:
    rows = []
    for _, row in df_novels.iterrows():
        if genre not in row['genre_list']:
            continue
        title  = row['query_title']
        pub_yr = row['original_publication_year']
        if pub_yr < 1800:
            continue
        s      = all_series[title]
        s_post = s[s.index >= pub_yr].copy()
        s_post.index = s_post.index - pub_yr
        if len(s_post) < EARLY_WINDOW:   # still require at least 35 years of data
            continue
        mx = s_post.max()
        if mx == 0:
            continue
        s_norm    = s_post / mx
        s_aligned = s_norm.reindex(pd.RangeIndex(LIFECYCLE_WINDOW), fill_value=np.nan)
        rows.append(s_aligned.values)

    if len(rows) < 3:
        continue
    mat = np.array(rows)
    n_at_age = np.sum(~np.isnan(mat), axis=0)
    mean_arr = np.where(n_at_age >= 3, np.nanmean(mat, axis=0), np.nan)
    p25_arr  = np.where(n_at_age >= 3, np.nanpercentile(mat, 25, axis=0), np.nan)
    p75_arr  = np.where(n_at_age >= 3, np.nanpercentile(mat, 75, axis=0), np.nan)
    genre_lifecycle[genre] = {
        'n': len(rows), 'mean': mean_arr, 'p25': p25_arr, 'p75': p75_arr,
    }
    print(f"  {genre}: {len(rows)} novels")

ages = np.arange(LIFECYCLE_WINDOW)

fig, ax = plt.subplots(figsize=(14, 6))
for genre, data in genre_lifecycle.items():
    color = genre_color[genre]

    ax.plot(ages, data['mean'], color=color, linewidth=1.8,
            label=f"{genre} (n={data['n']})")

ax.set_xlabel('Years since publication')
ax.set_ylabel('Normalized frequency (0–1, each novel scaled to own all-time max)')
ax.set_title(f'Genre lifecycle curves — {LIFECYCLE_WINDOW} years after publication\n'
             f'(English Ngram corpus; lines fade where fewer than 3 novels have data)')
ax.set_xlim(0, LIFECYCLE_WINDOW - 1)
ax.set_ylim(bottom=0)
ax.legend(fontsize=7.5, loc='upper right', ncol=2)
plt.tight_layout()
plt.savefig('figures/genre_lifecycle.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved → figures/genre_lifecycle.png\n")

os.makedirs('articles/data/genre', exist_ok=True)
_lc_series = {g: [None if np.isnan(v) else round(float(v), 6) for v in d['mean']] for g, d in genre_lifecycle.items()}
_lc_counts = {g: d['n'] for g, d in genre_lifecycle.items()}
with open('articles/data/genre/lifecycle.json', 'w') as _f:
    json.dump({'years': list(range(LIFECYCLE_WINDOW)), 'series': _lc_series, 'counts': _lc_counts,
               'xLabel': 'Years since publication', 'yLabel': 'Normalized frequency (0\u20131)', 'events': {}}, _f)
print("Saved \u2192 articles/data/genre/lifecycle.json\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1b — Genre lifecycle on calendar timeline (1850–2019)
# Same per-novel normalization as Analysis 1 (÷ own peak), but each novel is
# placed on a fixed year grid so the x-axis is an actual date.
# Pre-publication years are NaN; the average thins for earlier years naturally.
# ═══════════════════════════════════════════════════════════════════════════════
CAL_START = 1850
cal_idx   = pd.RangeIndex(CAL_START, REAL_END + 1)

genre_cal = {}
for genre in top_genres:
    rows = []
    for _, row in df_novels.iterrows():
        if genre not in row['genre_list']:
            continue
        title  = row['query_title']
        pub_yr = row['original_publication_year']
        s      = all_series[title]
        s_post = s[s.index >= pub_yr]
        if s_post.empty or len(s_post) < EARLY_WINDOW or s_post.max() == 0:
            continue
        s_norm    = s_post.reindex(cal_idx)   # NaN before pub_yr
        rows.append(s_norm.values)

    if len(rows) < 3:
        continue
    mat       = np.array(rows, dtype=float)
    n_present = np.sum(~np.isnan(mat), axis=0)
    mean_arr  = np.where(n_present >= 3, np.nanmean(mat, axis=0), np.nan)
    p25_arr   = np.where(n_present >= 3, np.nanpercentile(mat, 25, axis=0), np.nan)
    p75_arr   = np.where(n_present >= 3, np.nanpercentile(mat, 75, axis=0), np.nan)
    genre_cal[genre] = {'n': len(rows), 'mean': mean_arr, 'p25': p25_arr, 'p75': p75_arr}

cal_years = np.array(cal_idx)

fig, ax = plt.subplots(figsize=(14, 6))
for genre, data in genre_cal.items():
    color = genre_color[genre]

    ax.plot(cal_years, data['mean'], color=color, linewidth=1.8,
            label=f"{genre} (n={data['n']})")

ax.set_xlabel('Year')
ax.set_ylabel('Mean Ngram frequency (raw, averaged across novels in genre)')
ax.set_title(f'Genre lifecycle curves on calendar timeline ({CAL_START}–{REAL_END})\n'
             f'(raw frequencies — genres are directly comparable; lines fade where fewer than 3 novels have data)')
ax.set_xlim(CAL_START, REAL_END)
ax.set_ylim(bottom=0)
ax.legend(fontsize=7.5, loc='upper right', ncol=2)
plt.tight_layout()
plt.savefig('figures/genre_lifecycle_calendar.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved → figures/genre_lifecycle_calendar.png\n")

_cal_series =  {
    g: [None if np.isnan(v) else float(v) for v in d['mean']]
    for g, d in genre_cal.items()
}
_cal_counts = {g: d['n'] for g, d in genre_cal.items()}
with open('articles/data/genre/lifecycle_calendar.json', 'w') as _f:
    json.dump({'years': list(map(int, cal_years)), 'series': _cal_series, 'counts': _cal_counts,
               'xLabel': 'Year', 'yLabel': 'Mean Ngram frequency (raw)', 'events': {}}, _f)
print("Saved \u2192 articles/data/genre/lifecycle_calendar.json\n")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2 — Genre Ngram trends over real time (1900–2019)
# Each novel normalized by its own mean across 1900–2019
# (so 1.0 = that novel's average level; > 1.0 means above-average activity).
# Averaging within genre shows whether a genre is rising or falling as a
# cultural reference point.
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("ANALYSIS 2 — Genre cultural trends over real time (1900–2019)")
print("=" * 70)

real_idx   = pd.RangeIndex(REAL_START, REAL_END + 1)
genre_real = {}

for genre in top_genres:
    rows = []
    for _, row in df_novels.iterrows():
        if genre not in row['genre_list']:
            continue
        title  = row['query_title']
        pub_yr = row['original_publication_year']
        s      = all_series[title]

        # Zero-fill pre-publication years within the real window
        s_aligned = s.reindex(real_idx, fill_value=0.0)
        if pub_yr > REAL_START:
            s_aligned.loc[REAL_START:pub_yr - 1] = 0.0

        mean_val = s_aligned.mean()
        if mean_val == 0:
            continue

        rows.append((s_aligned / mean_val).values)  # normalize by own mean

    if len(rows) < 3:
        continue

    mat = np.array(rows)
    # Smooth each genre's mean with a 7-year rolling window
    mean_raw = pd.Series(np.nanmean(mat, axis=0), index=real_idx)
    mean_sm  = mean_raw.rolling(7, center=True, min_periods=4).mean()

    genre_real[genre] = {
        'n':    len(rows),
        'mean': mean_sm,
        'p25':  pd.Series(np.nanpercentile(mat, 25, axis=0), index=real_idx)
                  .rolling(7, center=True, min_periods=4).mean(),
        'p75':  pd.Series(np.nanpercentile(mat, 75, axis=0), index=real_idx)
                  .rolling(7, center=True, min_periods=4).mean(),
    }
    print(f"  {genre}: {len(rows)} novels")

years = list(real_idx)

fig, ax = plt.subplots(figsize=(14, 6))
ax.axhline(1.0, color='black', linewidth=0.7, linestyle='--', alpha=0.4,
           label='Baseline (each genre\'s own long-run mean)')

for genre, data in genre_real.items():
    color = genre_color[genre]

    ax.plot(years, data['mean'], color=color, linewidth=1.8,
            label=f"{genre} (n={data['n']})")

ax.set_xlabel('Year')
ax.set_ylabel('Normalized Ngram activity\n(1.0 = each genre\'s long-run mean; > 1.0 = above average)')
ax.set_title('Are classic genres rising or falling as cultural reference points?\n'
             f'(English Ngram corpus, 1900–2019, 7-year smoothing)')
ax.set_xlim(REAL_START, REAL_END)
ax.legend(fontsize=7.5, loc='upper left', ncol=2)
plt.tight_layout()
plt.savefig('figures/genre_trends.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved → figures/genre_trends.png")

_trend_series = {g: [None if np.isnan(v) else round(float(v), 6) for v in d['mean'].values] for g, d in genre_real.items()}
_trend_counts = {g: d['n'] for g, d in genre_real.items()}
with open('articles/data/genre/trends.json', 'w') as _f:
    json.dump({'years': list(range(REAL_START, REAL_END + 1)), 'series': _trend_series, 'counts': _trend_counts,
               'baseline': 1.0, 'xLabel': 'Year',
               'yLabel': 'Normalized Ngram activity (1.0\u202f=\u202flong-run mean)', 'events': {}}, _f)
print("Saved \u2192 articles/data/genre/trends.json")
