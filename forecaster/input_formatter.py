"""
Formats OHLCV DataFrames into the 7-tensor input that LaT-PFN's
``create_forecast`` method expects.

Tensor layout
─────────────
Context (example series — correlated assets providing in-context learning):
  T_context_history : [1, n_ctx, n_history, 1]
  T_context_prompt  : [1, n_ctx, n_prompt,  1]
  V_context_history : [1, n_ctx, n_history, 1]
  V_context_prompt  : [1, n_ctx, n_prompt,  1]

Heldout (target series — what we want to forecast):
  T_heldout_history : [1, n_held, n_history, 1]
  T_heldout_prompt  : [1, n_held, n_prompt,  1]
  V_heldout_history : [1, n_held, n_history, 1]

Strategy
────────
- The 4 heldout series are the target instrument's Open, High, Low, Close,
  using the LAST ``n_history`` bars. The prompt window is the true, unknown
  future (next ``n_prompt`` bars) — this is what the model forecasts.
- Context series are COMPLETE ``n_history + n_prompt`` windows that ended in
  the past (lagged windows of the target itself and of related assets), so
  their "prompt" segment is genuinely known. This mirrors LaT-PFN's own
  real-data evals, which use prior years of the same series as context.
- ``context_mode="legacy"`` reproduces the pre-2026-08-26 behaviour (target's
  last 60 bars discarded and "forecast"; contemporaneous context) for A/B
  comparison only. It does not forecast forward and must not be traded.
"""

from typing import Dict, List

import numpy as np
import pandas as pd
import torch

from market_data.normalizer import normalize_values, normalize_time, NormStats

# Columns used as the 4 heldout series for the target instrument
HELDOUT_COLS = ["Open", "High", "Low", "Close"]


def required_bars(n_history: int, n_prompt: int, n_context: int = 12,
                  context_stride: int | None = None, context_mode: str = "lagged") -> int:
    """Bars of target history needed to build a full self-context set."""
    total = n_history + n_prompt
    if context_mode == "legacy":
        return total
    stride = context_stride or n_prompt
    return total + max(0, n_context - 1) * stride


def _lagged_windows(values: np.ndarray, total: int, stride: int, max_windows: int) -> List[np.ndarray]:
    """Complete ``total``-length windows ending at t, t-stride, t-2*stride, ..."""
    out: List[np.ndarray] = []
    end = len(values)
    while end >= total and len(out) < max_windows:
        out.append(values[end - total:end].astype(np.float32))
        end -= stride
    return out


def format_inputs(
    heldout_df: pd.DataFrame,
    context_dfs: Dict[str, pd.DataFrame],
    n_history: int = 180,
    n_prompt: int = 60,
    min_context: int = 2,
    n_context: int = 12,
    context_stride: int | None = None,
    context_mode: str = "lagged",
) -> tuple[dict, NormStats]:
    """
    Build the 7 tensors required by ``LaTPFNV4.create_forecast()``.

    Args:
        heldout_df:  Target instrument OHLCV. Needs >= n_history rows for the
                     query; more rows (see ``required_bars``) give more lagged
                     self-context windows.
        context_dfs: {symbol: OHLCV DataFrame} for related assets (Close used).
        n_history:   History length (default 180).
        n_prompt:    Forecast horizon (default 60).
        min_context: Minimum context series (model needs dim > 1).
        n_context:   Target number of context series (train config: 16 - 4 heldout).
        context_stride: Bars between successive lagged windows (default n_prompt).
        context_mode: "lagged" (forecast forward) | "legacy" (old misaligned).

    Returns:
        (tensors_dict, close_stats)
    """
    total = n_history + n_prompt
    stride = context_stride or n_prompt

    T_full = normalize_time(total)
    T_hist = T_full[:n_history]
    T_prom = T_full[n_history:]

    # ── Heldout query (O, H, L, C of target) ──────────────────────────
    heldout_arrays = []
    close_stats = None
    for col in HELDOUT_COLS:
        if context_mode == "legacy":
            # Old behaviour: window of `total`, first n_history used, last
            # n_prompt bars discarded and treated as the "future".
            vals = heldout_df[col].values[-total:].astype(np.float32)
            v_norm, stats = normalize_values(vals)
            v_norm = v_norm[:n_history]
        else:
            vals = heldout_df[col].values[-n_history:].astype(np.float32)
            if len(vals) < n_history:
                raise ValueError(
                    f"heldout needs >= {n_history} bars, got {len(vals)}"
                )
            v_norm, stats = normalize_values(vals)
        heldout_arrays.append(v_norm)
        if col == "Close":
            close_stats = stats

    V_heldout_hist = np.stack(heldout_arrays)  # (4, n_history)
    T_heldout_hist = np.tile(T_hist, (len(HELDOUT_COLS), 1))
    T_heldout_prom = np.tile(T_prom, (len(HELDOUT_COLS), 1))

    # ── Context series ────────────────────────────────────────────────
    ctx_history_V: List[np.ndarray] = []
    ctx_prompt_V: List[np.ndarray] = []

    def _add(window: np.ndarray):
        v_norm, _ = normalize_values(window)
        ctx_history_V.append(v_norm[:n_history])
        ctx_prompt_V.append(v_norm[n_history:])

    if context_mode == "legacy":
        for symbol, df in context_dfs.items():
            close = df["Close"].values[-total:].astype(np.float32)
            if len(close) < total:
                continue
            _add(close)
    else:
        # Self-context first: the target's own completed windows, most recent
        # first. These end at the query's last bar, so their prompt segment is
        # fully known (it is the last n_prompt bars of the query's history).
        self_close = heldout_df["Close"].values.astype(np.float32)
        self_windows = _lagged_windows(self_close, total, stride, n_context)
        # Related-asset windows, round-robin by lag so the most recent window
        # of every asset comes before the second-most-recent of any.
        asset_windows = []
        for symbol, df in context_dfs.items():
            close = df["Close"].values.astype(np.float32)
            asset_windows.append(_lagged_windows(close, total, stride, n_context))
        # Interleave: self[0], asset windows lag-0, self[1], asset windows lag-1 ...
        max_lag = max([len(self_windows)] + [len(w) for w in asset_windows] + [0])
        for k in range(max_lag):
            if k < len(self_windows):
                _add(self_windows[k])
            for w in asset_windows:
                if k < len(w):
                    _add(w[k])
        ctx_history_V = ctx_history_V[:n_context]
        ctx_prompt_V = ctx_prompt_V[:n_context]

    if not ctx_history_V:
        raise ValueError(
            "No valid context series available. Need at least 1 complete "
            f"{total}-bar window from the target or a context asset."
        )
    while len(ctx_history_V) < min_context:
        ctx_history_V.append(ctx_history_V[0])
        ctx_prompt_V.append(ctx_prompt_V[0])

    n_ctx = len(ctx_history_V)

    V_ctx_hist = np.stack(ctx_history_V)  # (n_ctx, n_history)
    V_ctx_prom = np.stack(ctx_prompt_V)   # (n_ctx, n_prompt)
    T_ctx_hist = np.tile(T_hist, (n_ctx, 1))
    T_ctx_prom = np.tile(T_prom, (n_ctx, 1))

    # ── Convert to tensors [1, n_series, seq_len, 1] ─────────────────
    def to_tensor(arr: np.ndarray) -> torch.Tensor:
        return torch.from_numpy(arr).float().unsqueeze(0).unsqueeze(-1)

    tensors = {
        "T_context_history": to_tensor(T_ctx_hist),
        "T_context_prompt":  to_tensor(T_ctx_prom),
        "V_context_history": to_tensor(V_ctx_hist),
        "V_context_prompt":  to_tensor(V_ctx_prom),
        "T_heldout_history": to_tensor(T_heldout_hist),
        "T_heldout_prompt":  to_tensor(T_heldout_prom),
        "V_heldout_history": to_tensor(V_heldout_hist),
    }

    return tensors, close_stats
