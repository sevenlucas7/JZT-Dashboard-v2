#!/usr/bin/env python3
"""JZT Dashboard V2 Renderer - 京准通数据看板第二版

V2 特性：
- 历史数据日期选择（动态加载）
- 可读性改进（字号、间距）
- 与 V1 完全隔离的独立仓库

Usage:
    python3 jzt_dashboard_renderer_v2.py --split-data ~/JZT-Dashboard-v2/data/latest_split.json --output ~/JZT-Dashboard-v2/index.html
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

# Import V1 renderer functions for reuse
import sys
sys.path.insert(0, str(Path(__file__).parent))
from jzt_dashboard_renderer import (
    build_html_dashboard,
    load_painter_head,
    build_account_stats,
    LEGACY_ACCOUNTS,
    PWD_ACCOUNTS,
    ACCOUNT_ORDER,
    safe_float,
    money,
    roi_txt,
    short_money,
    status_class,
    roi_chip,
    delta_badge,
    delta_badge_small,
    sku_delta_chip,
    get_account_deltas,
    get_sku_deltas,
    get_sku_metric_delta,
    get_overall_deltas,
    get_format_deltas,
    get_ht_deltas,
    pct_value,
    markdown_to_plain,
    esc,
    fmt_num,
    TARGETS,
)


# V2 专用 CSS - 可读性改进
V2_READABILITY_CSS = """
  /* ================================================================
     V2 READABILITY IMPROVEMENTS
     核心数字加大、间距优化、可读性增强
  ================================================================ */

  /* KPI 核心数字加大 */
  .kpi-card .value {
    font-size: 36px !important;  /* 原 30px → 36px */
  }
  .kpi-card .value .unit {
    font-size: 22px !important;  /* 原 18px → 22px */
  }

  /* 账户卡片数字加大 */
  .acct-card .kpi-cell .v {
    font-size: 22px !important;  /* 原 17px → 22px */
  }

  /* Series 卡片数字加大 */
  .series-card .kpi-cell .v {
    font-size: 24px !important;  /* 原 20px → 24px */
  }

  /* SKU 表格数字加大 */
  .sku-table td.num {
    font-size: 13.5px !important;  /* 原 12px → 13.5px */
  }

  /* ROI chip 数字加大 */
  .roi-chip {
    font-size: 13px !important;  /* 原 12px → 13px */
    padding: 3px 9px !important;
  }

  /* KPI 卡片间距增加 */
  .kpi-strip {
    gap: 20px !important;  /* 原 14px → 20px */
    margin-bottom: 32px !important;
  }
  .kpi-card {
    padding: 20px 22px 18px !important;
  }

  /* 账户卡片间距增加 */
  .accounts-grid {
    gap: 16px !important;  /* 原 12px → 16px */
    margin-bottom: 36px !important;
  }
  .acct-card .body {
    padding: 16px 18px 18px !important;
  }

  /* Series 卡片间距 */
  .series-grid {
    gap: 18px !important;
    margin-bottom: 32px !important;
  }
  .series-card .series-body {
    padding: 16px 20px 18px !important;
  }

  /* SKU 行高增加 */
  .sku-table td {
    padding: 12px 14px !important;  /* 原 10px 12px → 12px 14px */
  }
  .sku-table tbody tr {
    min-height: 44px !important;
  }

  /* Format 卡片数字加大 */
  .fmt-value {
    font-size: 22px !important;  /* 原 18px → 22px */
  }

  /* —— DATE SELECTOR (header right, compact) —— */
  .date-selector {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .date-selector select {
    padding: 4px 28px 4px 10px;
    border: 1px solid var(--rule);
    border-radius: 6px;
    font-size: 11.5px;
    font-family: 'Inter', 'Noto Sans SC', sans-serif;
    background: var(--bg-soft);
    color: var(--ink-1);
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%235a5a58' d='M5 7L1 3h8z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    transition: border-color 0.15s, box-shadow 0.15s;
    min-width: 110px;
  }
  .date-selector select:hover {
    border-color: var(--brand);
  }
  .date-selector select:focus {
    outline: none;
    border-color: var(--brand);
    box-shadow: 0 0 0 2px var(--brand-soft);
  }
  .date-selector .live-dot {
    width: 6px;
    height: 6px;
    background: var(--ok);
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* Loading 状态 */
  .loading-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(250,250,248,0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    backdrop-filter: blur(4px);
  }
  .loading-overlay.hidden { display: none; }
  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--rule);
    border-top-color: var(--brand);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Footer 版本标识 */
  .footer .version-mark {
    background: linear-gradient(135deg, #0075de, #00c7be);
    color: #fff;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    margin-left: 8px;
  }
"""


def build_date_selector_html(dates_index: dict, current_date: str) -> str:
    """Build the date selector HTML.

    Args:
        dates_index: The dates_index.json dict
        current_date: Currently selected date string (YYYY-MM-DD)

    Returns:
        HTML string for the date selector
    """
    available = dates_index.get("available_dates", [])
    latest_date = dates_index.get("latest", current_date)

    options = []
    for item in sorted(available, key=lambda x: x["date"], reverse=True):
        date_str = item["date"]
        slot = item["slot"]
        label = f"{date_str}"
        selected = 'selected="selected"' if date_str == current_date else ''
        options.append(f'<option value="{date_str}" {selected}>{label}</option>')

    options_html = "\n".join(options)
    is_live = current_date == latest_date

    # Compact version for header-right placement
    return f'''<span class="date-selector"><select id="date-select" onchange="loadDateData(this.value)">{options_html}</select><span class="live-dot" id="live-dot" style="{"display:inline-block" if is_live else "display:none"}></span></span>'''


def build_v2_html(
    skus: list[dict],
    split_data: dict | None = None,
    meta: dict | None = None,
    suggestions: list[str] | None = None,
    dates_index: dict | None = None,
    current_date: str | None = None,
) -> str:
    """Build V2 HTML with date selector and readability improvements.

    Args:
        skus: List of SKU dicts
        split_data: Full split.json dict
        meta: Report meta info
        suggestions: Optional list of insight strings
        dates_index: dates_index.json dict for date selector
        current_date: Currently selected date (YYYY-MM-DD)
    """
    # Build date selector
    date_selector = ""
    if dates_index:
        date_selector = build_date_selector_html(dates_index, current_date or "")

    # Build the main dashboard HTML using V1 renderer
    dashboard_html = build_html_dashboard(skus, split_data, meta, suggestions)

    # Extract head from V1 renderer (which already has V1 CSS)
    head = load_painter_head()

    # Insert V2 readability CSS
    v2_css = V2_READABILITY_CSS
    if "</style>" in head:
        head = head.replace("</style>", v2_css + "\n  </style>", 1)
    else:
        head = head + f"<style>{v2_css}</style>"

    # Extract body content from V1 dashboard
    if "<body>" in dashboard_html:
        body_start = dashboard_html.index("<body>") + len("<body>")
    else:
        body_start = dashboard_html.index("<html lang=") + len("<html lang=>")

    body_content = dashboard_html[body_start:]

    # Inject date selector into header-right area, before the live-pill
    new_body = body_content
    if '<span class="live-pill">' in body_content:
        # Replace the live-pill span with date-selector + live-pill
        live_pill_pos = body_content.index('<span class="live-pill">')
        new_body = body_content[:live_pill_pos] + date_selector + body_content[live_pill_pos:]
    else:
        new_body = date_selector + body_content

    # Add V2 version badge to footer
    new_body = new_body.replace(
        '<span class="brand-mark">',
        '<span class="brand-mark">'
    ).replace(
        "Hermes Atelier</span>",
        'Hermes Atelier <span class="version-mark">V2</span></span>'
    )

    # Add loading overlay at the end of body
    loading_overlay = '<div class="loading-overlay hidden" id="loading"><div class="loading-spinner"></div></div>'
    if "</body>" in new_body:
        new_body = new_body.replace("</body>", loading_overlay + "\n</body>")
    else:
        new_body = new_body + loading_overlay

    # Add V2 JavaScript for dynamic date loading
    v2_js = build_v2_javascript()
    if "</body>" in new_body:
        new_body = new_body.replace("</body>", v2_js + "\n</body>")
    else:
        new_body = new_body + v2_js

    return "<!doctype html>\n<html lang=\"zh-CN\">\n" + head + "\n" + new_body


def build_v2_javascript() -> str:
    """Build the V2 JavaScript for dynamic date loading."""
    return '''
<script>
// ================================================================
// JZT Dashboard V2 - Dynamic Date Loading
// ================================================================

// Global state
let currentSplitData = null;
let currentMeta = null;
let datesIndex = null;
let isLoading = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  loadDatesIndex();
});

// Load the dates index
async function loadDatesIndex() {
  try {
    const resp = await fetch('./data/dates_index.json');
    if (!resp.ok) throw new Error('Failed to load dates_index.json');
    datesIndex = await resp.json();

    // Set current date from latest if not set
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = urlParams.get('date');

    if (dateParam) {
      loadDateData(dateParam);
    }
  } catch (e) {
    console.warn('Could not load dates_index.json:', e.message);
  }
}

// Load data for a specific date
async function loadDateData(dateStr) {
  if (isLoading) return;
  if (!datesIndex) {
    await loadDatesIndex();
  }

  const targetDate = datesIndex?.available_dates?.find(d => d.date === dateStr);
  if (!targetDate) {
    console.warn('Date not found in index:', dateStr);
    return;
  }

  isLoading = true;
  showLoading(true);

  try {
    const splitFile = targetDate.split_file;
    const resp = await fetch('./data/' + splitFile);
    if (!resp.ok) throw new Error('Failed to load ' + splitFile);
    const splitData = await resp.json();

    currentSplitData = splitData;

    // Update URL
    const url = new URL(window.location.href);
    url.searchParams.set('date', dateStr);
    window.history.replaceState({}, '', url);

    // Update page title
    document.title = '京准通数据看板 V2 · ' + dateStr;

    // Update live badge
    const liveBadge = document.getElementById('live-badge');
    const isLatest = dateStr === datesIndex?.latest;
    if (liveBadge) {
      liveBadge.style.display = isLatest ? 'inline-flex' : 'none';
    }

    // Re-render dashboard
    renderDashboard(splitData);

  } catch (e) {
    console.error('Error loading date data:', e);
    alert('加载数据失败: ' + e.message);
  } finally {
    isLoading = false;
    showLoading(false);
  }
}

// Re-render the dashboard with new data
function renderDashboard(splitData) {
  // Find the main content areas to update
  // We need to rebuild key sections: kpi-strip, series-grid, accounts-grid, detail cards

  const accountVisuals = {
    "GMEC-Tide-L": {class: "tidel", badge: "tidel", brand: "Tide", color: "var(--c-tidel)"},
    "GMEC-Ariel-L": {class: "ariell", badge: "ariell", brand: "Ariel", color: "var(--c-ariell)"},
    "GMEC-Tide": {class: "tide", badge: "tide", brand: "Tide", color: "var(--c-tide)"},
    "GMEC-Ariel": {class: "ariel", badge: "ariel", brand: "Ariel", color: "var(--c-ariel)"},
    "GMEC-Downy": {class: "downy", badge: "downy", brand: "Downy", color: "var(--c-downy)"},
  };

  const skus = splitData.skus || [];
  const accountStats = buildAccountStats(skus, splitData);

  // Update KPI strip
  updateKPIStrip(accountStats, splitData);

  // Update series cards
  updateSeriesCards(accountStats, splitData);

  // Update account cards
  updateAccountCards(accountStats, splitData, accountVisuals);

  // Update detail cards
  updateDetailCards(accountStats, splitData, accountVisuals);

  // Update meta bar
  updateMetaBar(splitData);

  // Update suggestions
  updateSuggestions(splitData);
}

function buildAccountStats(skus, splitData) {
  const byAccount = {};
  for (const s of skus) {
    byAccount[s.账户] = byAccount[s.账户] || [];
    byAccount[s.账户].push(s);
  }
  const htMap = {};
  for (const h of (splitData.ht || [])) {
    htMap[h.账户] = h;
  }

  const stats = [];
  for (const account of ACCOUNT_ORDER) {
    const accSkus = byAccount[account] || [];
    if (!accSkus.length) continue;

    const target = TARGETS[account] || 2.5;
    const htRow = htMap[account] || {};
    const htSpend = safeFloat(htRow['HT花费(SPD)'] || 0);
    const htRoiVal = safeFloat(htRow['HT ROI'] || 0);
    const skuSpend = accSkus.reduce((sum, s) => sum + safeFloat(s['综合花费(SPD)'] || 0), 0);
    const skuRev = accSkus.reduce((sum, s) => sum + safeFloat(s['综合花费(SPD)'] || 0) * safeFloat(s['综合ROI(含JST+SEM)'] || 0), 0);
    const htRev = htSpend * htRoiVal;
    const totalSpend = skuSpend + htSpend;
    const totalRev = skuRev + htRev;
    const jstSpend = accSkus.reduce((sum, s) => sum + safeFloat(s['JST花费(SPD)'] || 0), 0);
    const semSpend = accSkus.reduce((sum, s) => sum + safeFloat(s['SEM花费(SPD)'] || 0), 0);

    stats.push({
      account,
      skus: accSkus,
      target,
      totalSpend,
      totalRev,
      avgRoi: totalRev / totalSpend || 0,
      htSpend,
      htRoiVal,
      jstSpend,
      semSpend,
    });
  }
  return stats;
}

function updateKPIStrip(accountStats, splitData) {
  const totalAllSpend = accountStats.reduce((sum, a) => sum + a.totalSpend, 0);
  const totalAllRev = accountStats.reduce((sum, a) => sum + a.totalRev, 0);
  const weightedRoi = totalAllRev / totalAllSpend || 0;
  const lowAccounts = accountStats.filter(a => a.avgRoi < a.target).length;

  const kpiStrip = document.querySelector('.kpi-strip');
  if (!kpiStrip) return;

  // Update total spend
  const blueCard = kpiStrip.querySelector('.b-blue .value');
  if (blueCard) {
    blueCard.innerHTML = '<span class="unit">¥</span>' + totalAllSpend.toLocaleString('zh-CN');
  }

  // Update ROI
  const greenCard = kpiStrip.querySelector('.b-green .value');
  if (greenCard) {
    greenCard.textContent = weightedRoi.toFixed(2);
  }

  // Update low accounts count
  const redCard = kpiStrip.querySelector('.b-red .value');
  if (redCard) {
    redCard.textContent = lowAccounts;
  }
}

function updateSeriesCards(accountStats, splitData) {
  // Legacy = Tide-L + Ariel-L
  // PWD = Tide + Ariel
  const legacyStats = accountStats.filter(a => a.account === 'GMEC-Tide-L' || a.account === 'GMEC-Ariel-L');
  const pwdStats = accountStats.filter(a => a.account === 'GMEC-Tide' || a.account === 'GMEC-Ariel');

  const seriesGrid = document.querySelector('.series-grid');
  if (!seriesGrid) return;

  const cards = seriesGrid.querySelectorAll('.series-card');
  cards.forEach(card => {
    const name = card.querySelector('.series-name');
    if (!name) return;
    const seriesName = name.textContent.trim().split(' ')[0];

    let stats;
    if (seriesName === 'Legacy') stats = legacyStats;
    else if (seriesName === 'PWD') stats = pwdStats;
    else return;

    const totalSpend = stats.reduce((sum, a) => sum + a.totalSpend, 0);
    const totalRev = stats.reduce((sum, a) => sum + a.totalRev, 0);
    const roi = totalRev / totalSpend || 0;

    const cells = card.querySelectorAll('.kpi-cell .v');
    if (cells[0]) cells[0].textContent = money(totalSpend);
    if (cells[1]) cells[1].textContent = roi.toFixed(2);
  });
}

function updateAccountCards(accountStats, splitData, accountVisuals) {
  const accountsGrid = document.querySelector('.accounts-grid');
  if (!accountsGrid) return;

  const cards = accountsGrid.querySelectorAll('.acct-card');
  cards.forEach(card => {
    const nameEl = card.querySelector('.name');
    if (!nameEl) return;
    const accountName = nameEl.textContent.trim().split(' ')[0];

    const stat = accountStats.find(a => a.account === accountName);
    if (!stat) return;

    const cells = card.querySelectorAll('.kpi-cell .v');
    if (cells[0]) cells[0].textContent = money(stat.totalSpend);
    if (cells[1]) cells[1].textContent = stat.avgRoi.toFixed(2);
  });
}

function updateDetailCards(accountStats, splitData, accountVisuals) {
  const mainCol = document.querySelector('.main-col');
  if (!mainCol) return;

  const detailCards = mainCol.querySelectorAll('.account-detail-card');
  detailCards.forEach(detailCard => {
    const header = detailCard.querySelector('h3');
    if (!header) return;
    const accountName = header.textContent.trim().split(' ')[0];

    const stat = accountStats.find(a => a.account === accountName);
    if (!stat) return;

    const tbody = detailCard.querySelector('tbody');
    if (!tbody) return;

    // Update each SKU row
    const rows = tbody.querySelectorAll('tr:not(.ht-row)');
    rows.forEach(row => {
      const skuNameEl = row.querySelector('.sku-name');
      if (!skuNameEl) return;
      const skuName = skuNameEl.textContent.trim();

      const sku = stat.skus.find(s => s['SKU简称'] === skuName || s['SKU名称'] === skuName);
      if (!sku) return;

      const cells = row.querySelectorAll('td.num');
      if (cells[0]) cells[0].textContent = money(safeFloat(sku['综合花费(SPD)']));
      if (cells[1]) cells[1].innerHTML = roiChip(safeFloat(sku['综合ROI(含JST+SEM)']), stat.target);
      if (cells[2]) cells[2].textContent = money(safeFloat(sku['JST花费(SPD)']));
      if (cells[3]) cells[3].innerHTML = roiChip(safeFloat(sku['JST ROI']), stat.target, safeFloat(sku['JST花费(SPD)']));
      if (cells[4]) cells[4].textContent = money(safeFloat(sku['SEM花费(SPD)']));
      if (cells[5]) cells[5].innerHTML = roiChip(safeFloat(sku['SEM ROI']), stat.target, safeFloat(sku['SEM花费(SPD)']));
    });

    // Update HT row
    const htRow = tbody.querySelector('tr.ht-row');
    if (htRow && stat.htSpend > 0) {
      const cells = htRow.querySelectorAll('td.num');
      if (cells[0]) cells[0].textContent = money(stat.htSpend);
      if (cells[1]) cells[1].innerHTML = roiChip(stat.htRoiVal, stat.target, stat.htSpend);
    }
  });
}

function updateMetaBar(splitData) {
  const metaBar = document.querySelector('.meta-bar');
  if (!metaBar) return;

  const metaItems = metaBar.querySelectorAll('.meta-item .v');
  if (metaItems[0]) metaItems[0].textContent = splitData.generated_at || '—';
  if (metaItems[1]) metaItems[1].textContent = splitData.source_file || '—';
  if (metaItems[2]) metaItems[2].textContent = splitData.report_date + ' ' + splitData.slot_label || '—';
}

function updateSuggestions(splitData) {
  const insightsSection = document.querySelector('.insights-section');
  if (!insightsSection) return;
  // Suggestions require suggestions list from the data, keep as-is for now
}

function showLoading(show) {
  const loading = document.getElementById('loading');
  if (loading) {
    loading.classList.toggle('hidden', !show);
  }
}
</script>'''


def generate_suggestions(skus: list[dict], split_data: dict | None, targets: dict | None = None) -> list[str]:
    """Generate suggestions based on data - imported from jzt_deliver_feishu.py."""
    # Import from jzt_deliver_feishu if available
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / ".hermes" / "scripts" / "jingzhuntong"))
        from jzt_deliver_feishu import generate_suggestions as gen_sug
        return gen_sug(skus, split_data, targets)
    except Exception:
        return []


def parse_args_v2() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JZT Dashboard V2 Renderer")
    p.add_argument("--split-data", required=True, help="Path to split.json")
    p.add_argument("--output", required=True, help="Output HTML path")
    p.add_argument("--meta", help="Path to meta.json")
    p.add_argument("--dates-index", help="Path to dates_index.json")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args_v2()

    # Load split data
    with open(args.split_data) as f:
        split_data = json.load(f)

    skus = split_data.get("skus", [])
    meta = None
    if args.meta and Path(args.meta).exists():
        with open(args.meta) as f:
            meta = json.load(f)

    dates_index = None
    if args.dates_index and Path(args.dates_index).exists():
        with open(args.dates_index) as f:
            dates_index = json.load(f)

    current_date = split_data.get("report_date", "")

    # Generate HTML
    html = build_v2_html(skus, split_data, meta, [], dates_index, current_date)

    # Write output
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"V2 dashboard written to {args.output}")
