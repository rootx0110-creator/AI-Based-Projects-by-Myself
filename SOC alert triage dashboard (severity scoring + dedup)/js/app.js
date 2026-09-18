/* ============================================================
   SOC ALERT TRIAGE DASHBOARD - Main Application Controller
   ============================================================ */

const SOCApp = (() => {
  'use strict';

  /* ---------- Application State ---------- */
  const state = {
    alerts: [],
    allAlerts: [],
    filteredAlerts: [],
    selectedAlert: null,
    selectedIds: new Set(),
    filters: {
      severity: ['Critical', 'High', 'Medium', 'Low', 'Info'],
      sources: ['Suricata', 'CrowdStrike', 'Splunk', 'Windows Defender', 'AWS CloudTrail', 'Zeek'],
      statuses: ['New', 'Investigating', 'Resolved', 'False Positive'],
      timeRange: '24h',
      searchText: '',
      showDuplicates: false,
      autoMerge: true,
      minScore: 0
    },
    sort: { field: 'severity', direction: 'desc' },
    pagination: { currentPage: 1, pageSize: 25 },
    view: 'merged',
    timelineRange: '24h'
  };

  /* ---------- DOM element references ---------- */
  const el = {
    tableBody: document.getElementById('alertsTableBody'),
    emptyState: document.getElementById('emptyState'),
    paginationInfo: document.getElementById('paginationInfo'),
    pageIndicator: document.getElementById('pageIndicator'),
    prevPageBtn: document.getElementById('prevPageBtn'),
    nextPageBtn: document.getElementById('nextPageBtn'),
    pageSizeSelect: document.getElementById('pageSizeSelect'),
    severityDonut: document.getElementById('severityDonut'),
    severityBars: document.getElementById('severityBars'),
    severityLegend: document.getElementById('severityLegend'),
    donutCenterValue: document.getElementById('donutCenterValue'),
    donutCenterLabel: document.getElementById('donutCenterLabel'),
    timelineChart: document.getElementById('timelineChart'),
    globalSearch: document.getElementById('globalSearch'),
    minScoreFilter: document.getElementById('minScoreFilter'),
    minScoreLabel: document.getElementById('minScoreLabel'),
    timeRangeFilter: document.getElementById('timeRangeFilter'),
    showDuplicatesToggle: document.getElementById('showDuplicatesToggle'),
    autoMergeToggle: document.getElementById('autoMergeToggle'),
    filterCount: document.getElementById('filterCount'),
    queueCount: document.getElementById('queueCount'),
    sortLabel: document.getElementById('sortLabel')
  };

  /* ---------- Stats refs (by id) ---------- */
  const statId = id => document.getElementById(id);

  /* ---------- Initialization ---------- */
  function init() {
    bindEvents();
    state.allAlerts = SOCData.generateAlerts(480);
    state.alerts = state.allAlerts.slice();
    applyFilters();
    renderAll();
    showToast('Dashboard initialized', 'Loaded ' + state.allAlerts.length + ' alerts', 'success');
  }

  /* ---------- Event Binding ---------- */
  function bindEvents() {
    // Global search (debounced)
    el.globalSearch.addEventListener('input', debounce(() => {
      state.filters.searchText = el.globalSearch.value.trim().toLowerCase();
      applyFilters();
    }, 250));

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'k') { e.preventDefault(); el.globalSearch.focus(); }
      if (e.key === 'Escape') { closeDetail(); document.getElementById('kbdModal').style.display = 'none'; document.getElementById('reportModal').style.display = 'none'; }
      if (e.key === '?') { toggleKbdModal(); }
    });

    // Severity chips
    document.querySelectorAll('#severityFilter .chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const sev = chip.dataset.severity;
        const idx = state.filters.severity.indexOf(sev);
        if (idx > -1) {
          state.filters.severity.splice(idx, 1);
          chip.classList.remove('active');
        } else {
          state.filters.severity.push(sev);
          chip.classList.add('active');
        }
        applyFilters();
      });
    });

    // Status chips
    document.querySelectorAll('.chip-status').forEach(chip => {
      chip.addEventListener('click', () => {
        const st = chip.dataset.status;
        const idx = state.filters.statuses.indexOf(st);
        if (idx > -1) {
          state.filters.statuses.splice(idx, 1);
          chip.classList.remove('active');
        } else {
          state.filters.statuses.push(st);
          chip.classList.add('active');
        }
        applyFilters();
      });
    });

    // Source checkboxes
    document.querySelectorAll('.source-cb').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked && !state.filters.sources.includes(cb.dataset.source)) {
          state.filters.sources.push(cb.dataset.source);
        } else if (!cb.checked) {
          state.filters.sources = state.filters.sources.filter(s => s !== cb.dataset.source);
        }
        applyFilters();
      });
    });

    // Time range
    el.timeRangeFilter.addEventListener('change', () => {
      state.filters.timeRange = el.timeRangeFilter.value;
      applyFilters();
    });

    // Min score slider
    el.minScoreFilter.addEventListener('input', () => {
      state.filters.minScore = parseFloat(el.minScoreFilter.value);
      el.minScoreLabel.textContent = state.filters.minScore.toFixed(1);
      applyFilters();
    });

    // Dedup toggles
    el.showDuplicatesToggle.addEventListener('change', () => {
      state.filters.showDuplicates = el.showDuplicatesToggle.checked;
      applyFilters();
    });
    el.autoMergeToggle.addEventListener('change', () => {
      state.filters.autoMerge = el.autoMergeToggle.checked;
      applyFilters();
    });

    // Clear filters
    document.getElementById('clearFiltersBtn').addEventListener('click', resetFilters);

    // Export report
    document.getElementById('exportReportBtn').addEventListener('click', openReportModal);
    document.getElementById('generateReportBtn').addEventListener('click', () => {
      const opts = {
        includeSummary: document.getElementById('reportOptSummary').checked,
        includeStats: document.getElementById('reportOptStats').checked,
        includeAlerts: document.getElementById('reportOptAlerts').checked,
        includeDedup: document.getElementById('reportOptDedup').checked
      };
      downloadReport(opts);
    });
    document.getElementById('reportModal').addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-backdrop')) {
        document.getElementById('reportModal').style.display = 'none';
      }
    });

    // Refresh
    document.getElementById('refreshBtn').addEventListener('click', refreshData);

    // Sortable headers
    document.querySelectorAll('.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const field = th.dataset.sort;
        if (state.sort.field === field) {
          state.sort.direction = state.sort.direction === 'desc' ? 'asc' : 'desc';
        } else {
          state.sort = { field, direction: 'desc' };
        }
        applySort();
        renderTable();
      });
    });

    // Pagination
    el.prevPageBtn.addEventListener('click', () => changePage(-1));
    el.nextPageBtn.addEventListener('click', () => changePage(1));
    el.pageSizeSelect.addEventListener('change', () => {
      state.pagination.pageSize = parseInt(el.pageSizeSelect.value);
      state.pagination.currentPage = 1;
      renderTable();
    });

    // Detail panel
    document.getElementById('closeDetailBtn').addEventListener('click', closeDetail);
    document.getElementById('detailOverlay').addEventListener('click', closeDetail);
    document.getElementById('detailStatusSelect').addEventListener('change', (e) => {
      if (state.selectedAlert) {
        state.selectedAlert.status = e.target.value;
        updateDetailPanel(state.selectedAlert);
        renderTable();
        updateStats();
      }
    });
    document.getElementById('markDuplicateBtn').addEventListener('click', markAsDuplicate);

    // View toggles
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.view = btn.dataset.view;
        applyFilters();
      });
    });

    // Timeline range buttons
    document.querySelectorAll('.range-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.timelineRange = btn.dataset.range;
        renderTimeline();
      });
    });

    // Row select all
    document.getElementById('selectAllCheckbox').addEventListener('change', (e) => {
      if (e.target.checked) {
        state.filteredAlerts.forEach(a => state.selectedIds.add(a.id));
      } else {
        state.selectedIds.clear();
      }
      renderTable();
    });

    // Modal toggles
    document.getElementById('menuBtn').addEventListener('click', toggleKbdModal);
    document.getElementById('kbdModal').addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-backdrop')) {
        document.getElementById('kbdModal').style.display = 'none';
      }
    });

    // Empty state reset
    document.getElementById('emptyStateReset').addEventListener('click', resetFilters);
  }

  /* ---------- Filtering ---------- */
  function applyFilters() {
    let result = state.alerts.slice();

    // Severity filter
    if (state.filters.severity.length > 0) {
      result = result.filter(a => state.filters.severity.includes(a.severity));
    }

    // Source filter
    if (state.filters.sources.length > 0) {
      result = result.filter(a => state.filters.sources.includes(a.dataSource));
    }

    // Status filter
    if (state.filters.statuses.length > 0) {
      result = result.filter(a => state.filters.statuses.includes(a.status));
    }

    // Time range
    const rangeMs = {
      '1h': 3600000, '6h': 6 * 3600000, '24h': 24 * 3600000, '7d': 7 * 24 * 3600000
    };
    if (state.filters.timeRange !== 'all' && rangeMs[state.filters.timeRange]) {
      const cutoff = Date.now() - rangeMs[state.filters.timeRange];
      result = result.filter(a => new Date(a.timestamp).getTime() >= cutoff);
    }

    // Search text
    if (state.filters.searchText) {
      const q = state.filters.searchText;
      result = result.filter(a =>
        a.title.toLowerCase().includes(q) ||
        a.sourceIP.toLowerCase().includes(q) ||
        a.destIP.toLowerCase().includes(q) ||
        (a.mitre || '').toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q) ||
        a.threatType.toLowerCase().includes(q)
      );
    }

    // Min score
    result = result.filter(a => a.severityScore >= state.filters.minScore);

    // Dedup handling
    if (state.filters.autoMerge && state.view === 'merged') {
      // Keep original alerts; duplicates highlighted but shown once merged
      result = result.filter(a => !a.isDuplicate);
    } else if (!state.filters.showDuplicates) {
      result = result.filter(a => !a.isDuplicate);
    }

    state.filteredAlerts = result;
    state.pagination.totalItems = result.length;
    state.pagination.totalPages = Math.max(1, Math.ceil(result.length / state.pagination.pageSize));
    if (state.pagination.currentPage > state.pagination.totalPages) {
      state.pagination.currentPage = state.pagination.totalPages;
    }

    applySort();
    renderAll();
  }

  function applySort() {
    const { field, direction } = state.sort;
    const dir = direction === 'desc' ? -1 : 1;
    state.filteredAlerts.sort((a, b) => {
      let valA, valB;
      switch (field) {
        case 'severity': valA = SOCData.SEVERITY_ORDER.indexOf(a.severity); valB = SOCData.SEVERITY_ORDER.indexOf(b.severity); break;
        case 'score': valA = a.severityScore; valB = b.severityScore; break;
        case 'title': valA = a.title.toLowerCase(); valB = b.title.toLowerCase(); break;
        case 'source': valA = a.dataSource; valB = b.dataSource; break;
        case 'category': valA = a.category; valB = b.category; break;
        case 'status': valA = a.status; valB = b.status; break;
        case 'timestamp':
        default: valA = new Date(a.timestamp).getTime(); valB = new Date(b.timestamp).getTime(); break;
      }
      if (valA < valB) return -1 * dir;
      if (valA > valB) return 1 * dir;
      return 0;
    });
  }

  /* ---------- Rendering ---------- */
  function renderAll() {
    updateStats();
    renderTable();
    renderCharts();
    renderTimeline();
    updateFilterSummary();
  }

  /* ---------- Stats ---------- */
  function updateStats() {
    const all = state.alerts;
    const filtered = state.filteredAlerts;
    const total = all.length;
    const unique = all.filter(a => !a.isDuplicate).length;
    const dups = total - unique;
    const dedupRate = total ? Math.round((dups / total) * 100) : 0;

    const filteredTotal = filtered.length;
    const cr = filtered.filter(a => a.severity === 'Critical').length;
    const hi = filtered.filter(a => a.severity === 'High').length;
    const avg = filteredTotal ? (filtered.reduce((s, a) => s + a.severityScore, 0) / filteredTotal).toFixed(1) : '0.0';

    statId('statTotal').textContent = total;
    statId('statCritical').textContent = cr;
    statId('statHigh').textContent = hi;
    statId('statUnique').textContent = unique;
    statId('statAvgScore').textContent = avg;
    statId('statDedupRate').textContent = dedupRate + '% dedup';
    statId('statRiskScore').textContent = avg >= 7 ? 'HIGH RISK' : (avg >= 4 ? 'MED RISK' : 'LOW RISK');

    // Trends (simulated)
    const criticalPct = total ? Math.round((all.filter(a => a.severity === 'Critical').length / total) * 100) : 0;
    statId('statCriticalTrend').textContent = criticalPct + '% of total';
    statId('statHighTrend').textContent = total ? Math.round((all.filter(a => a.severity === 'High').length / total) * 100) + '% of total' : '0%';
    statId('statTotalTrend').textContent = total ? '+' + Math.round(total * 0.05) + ' this hr' : '0';

    el.queueCount.textContent = filteredTotal + ' alerts';
  }

  /* ---------- Table rendering ---------- */
  function renderTable() {
    const { currentPage, pageSize } = state.pagination;
    const start = (currentPage - 1) * pageSize;
    const pageItems = state.filteredAlerts.slice(start, start + pageSize);

    // Clear select-all
    document.getElementById('selectAllCheckbox').checked = false;

    if (state.filteredAlerts.length === 0) {
      el.tableBody.innerHTML = '';
      el.emptyState.style.display = 'block';
    } else {
      el.emptyState.style.display = 'none';
    }

    el.tableBody.innerHTML = pageItems.map((alert, i) => {
      const sevClass = 'sev-' + alert.severity.toLowerCase();
      const color = SOCData.getScoreColor(alert.severityScore);
      const selected = state.selectedIds.has(alert.id) ? 'selected' : '';
      const isDup = alert.isDuplicate;
      const dupLabel = isDup ? 'dup' : '';
      const rowNum = start + i;

      const relTime = SOCData.relativeTime(alert.timestamp);
      const dupBadge = isDup
        ? `<span class="dedup-badge-flag dup" title="Duplicate of ${alert.duplicateOf}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:10px"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg> DUP</span>`
        : (alert.dupCount > 0
          ? `<span class="dedup-badge-flag" title="${alert.dupCount} duplicates merged">${alert.dupCount + 1}×</span>`
          : `<span class="dedup-badge-flag" style="opacity:0.5">—</span>`);

      return `<tr class="${selected} ${isDup ? 'duplicate-row' : ''}" data-id="${alert.id}" style="animation-delay:${Math.min(i * 15, 300)}ms">
        <td class="col-check">
          <input type="checkbox" class="row-select" data-id="${alert.id}" ${selected ? 'checked' : ''} onclick="event.stopPropagation()">
        </td>
        <td class="col-severity">
          <span class="severity-badge ${sevClass}"><span class="sev-dot ${sevClass}"></span>${alert.severity}</span>
        </td>
        <td class="col-score">
          <span class="score-cell" style="color:${color}">${alert.severityScore.toFixed(1)}</span>
          <div class="score-bar-mini"><div class="score-bar-mini-fill" style="width:${alert.severityScore * 10}%;background:${color}"></div></div>
        </td>
        <td class="col-alert alert-title-cell">
          <span class="alert-title">${escHTML(alert.title)}</span>
          <span class="alert-subtitle mono">${alert.sourceIP} → ${alert.destIP} · ${alert.mitre}</span>
        </td>
        <td class="col-source"><span class="source-badge">${escHTML(alert.dataSource)}</span></td>
        <td class="col-ip mono">${alert.sourceIP}</td>
        <td class="col-category"><span class="category-tag">${escHTML(alert.category)}</span></td>
        <td class="col-status"><span class="status-badge st-${escHTML(alert.status).replace(/ /g, '-')}">${escHTML(alert.status)}</span></td>
        <td class="col-time" title="${alert.timestamp}">${relTime}</td>
        <td class="col-dedup">${dupBadge}</td>
        <td class="col-actions">
          <button class="row-action-btn" title="View details" onclick="event.stopPropagation(); SOCApp.openDetail('${alert.id}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </td>
      </tr>`;
    }).join('');

    // Update pagination controls
    const total = state.filteredAlerts.length;
    const end = Math.min(start + pageSize, total);
    el.paginationInfo.textContent = `Showing ${total ? start + 1 : 0}-${end} of ${total}`;
    el.pageIndicator.textContent = `${currentPage} / ${state.pagination.totalPages}`;
    el.prevPageBtn.disabled = currentPage <= 1;
    el.nextPageBtn.disabled = currentPage >= state.pagination.totalPages;

    // Update sort label
    const fieldLabels = { severity: 'Severity', score: 'Score', title: 'Alert', source: 'Source', category: 'Category', status: 'Status', timestamp: 'Time' };
    el.sortLabel.textContent = `${fieldLabels[state.sort.field] || ''} ${state.sort.direction === 'desc' ? '↓' : '↑'}`;

    // Update sort indicators
    document.querySelectorAll('.sortable').forEach(th => {
      const ind = th.querySelector('.sort-indicator');
      if (th.dataset.sort === state.sort.field) {
        ind.textContent = state.sort.direction === 'desc' ? '↓' : '↑';
      } else {
        ind.textContent = '';
      }
    });

    // Row click event delegation
    el.tableBody.querySelectorAll('tr[data-id]').forEach(tr => {
      tr.addEventListener('click', () => {
        const id = tr.dataset.id;
        const alert = state.alerts.find(a => a.id === id);
        if (alert) openDetail(id);
      });
    });

    // Row select events
    el.tableBody.querySelectorAll('.row-select').forEach(cb => {
      cb.addEventListener('change', () => {
        if (cb.checked) state.selectedIds.add(cb.dataset.id);
        else state.selectedIds.delete(cb.dataset.id);
      });
    });
  }

  /* ---------- Charts: Donut + Bars ---------- */
  function renderCharts() {
    const counts = { Critical: 0, High: 0, Medium: 0, Low: 0, Info: 0 };
    state.filteredAlerts.forEach(a => { counts[a.severity] = (counts[a.severity] || 0) + 1; });
    const total = state.filteredAlerts.length;

    el.donutCenterValue.textContent = total;
    el.donutCenterLabel.textContent = 'Alerts';

    // Build donut with conic-gradient
    const colors = ['#ff4757', '#ff9f43', '#fdcb6e', '#4dabf7', '#37d5de'];
    const sevOrder = ['Critical', 'High', 'Medium', 'Low', 'Info'];
    let accPercent = 0;
    const gradientParts = [];
    sevOrder.forEach((sev, i) => {
      const pct = total ? (counts[sev] / total) * 100 : 0;
      if (pct > 0) {
        const start = accPercent;
        const end = accPercent + pct;
        gradientParts.push(`${colors[i]} ${start}% ${end}%`);
        accPercent = end;
      }
    });
    if (gradientParts.length === 0) gradientParts.push('#1e293b 0% 100%');
    el.severityDonut.style.background = `conic-gradient(${gradientParts.join(', ')})`;

    // Legend
    el.severityLegend.innerHTML = sevOrder.map((sev, i) =>
      `<span class="legend-item"><span class="legend-dot" style="background:${colors[i]}"></span>${sev}</span>`
    ).join('');

    // Bars
    el.severityBars.innerHTML = sevOrder.map((sev, i) => {
      const count = counts[sev] || 0;
      const pct = total ? Math.round((count / total) * 100) : 0;
      return `<div class="severity-bar-row">
        <span class="severity-bar-label">${sev}</span>
        <div class="severity-bar-track">
          <div class="severity-bar-fill" style="width:${pct}%; background:${colors[i]}"></div>
        </div>
        <span class="severity-bar-count">${count}</span>
      </div>`;
    }).join('');
  }

  /* ---------- Timeline chart ---------- */
  function renderTimeline() {
    const rangeMs = { '6h': 6, '24h': 24, '7d': 168 };
    const hours = rangeMs[state.timelineRange] || 24;
    const now = Date.now();
    const start = now - hours * 3600000;

    const relevant = state.filteredAlerts.filter(a => new Date(a.timestamp).getTime() >= start);
    const buckets = new Array(hours).fill(0);

    relevant.forEach(a => {
      const t = new Date(a.timestamp).getTime();
      const hourIdx = Math.min(hours - 1, Math.max(0, Math.floor((hours - (now - t) / 3600000))));
      buckets[hourIdx]++;
    });

    const max = Math.max(...buckets, 1);
    el.timelineChart.innerHTML = buckets.map((count, i) => {
      const h = Math.max(3, Math.round((count / max) * 140));
      const hourNum = new Date(now - (hours - 1 - i) * 3600000).getHours();
      return `<div class="timeline-bar" style="height:${h}px" title="Hour ${hourNum}:00 - ${count} alerts">
        <span class="tooltip">${hourNum}:00 — ${count} alerts</span>
      </div>`;
    }).join('');
  }

  /* ---------- Filter summary ---------- */
  function updateFilterSummary() {
    el.filterCount.innerHTML = `Showing <strong>${state.filteredAlerts.length}</strong> of ${state.alerts.length} alerts`;
  }

  /* ---------- Detail panel ---------- */
  function openDetail(id) {
    const alert = state.alerts.find(a => a.id === id);
    if (!alert) return;
    state.selectedAlert = alert;
    document.getElementById('detailPanel').classList.add('open');
    document.getElementById('detailOverlay').classList.add('open');
    updateDetailPanel(alert);
  }

  function closeDetail() {
    state.selectedAlert = null;
    document.getElementById('detailPanel').classList.remove('open');
    document.getElementById('detailOverlay').classList.remove('open');
  }

  function updateDetailPanel(alert) {
    const badge = document.getElementById('detailSeverityBadge');
    badge.textContent = alert.severity.toUpperCase();
    badge.className = 'detail-severity-badge ' + (alert.severity === 'Critical' ? 'sev-critical' : alert.severity === 'High' ? 'sev-high' : alert.severity === 'Medium' ? 'sev-medium' : alert.severity === 'Low' ? 'sev-low' : 'sev-info');

    document.getElementById('detailTitle').textContent = alert.title;
    document.getElementById('detailAlertId').textContent = alert.id;
    document.getElementById('detailTimestamp').textContent = new Date(alert.timestamp).toLocaleString();
    document.getElementById('detailSource').textContent = alert.dataSource;
    document.getElementById('detailCategory').textContent = alert.category;
    document.getElementById('detailMitre').textContent = alert.mitre;
    document.getElementById('detailSrcIP').textContent = alert.sourceIP;
    document.getElementById('detailDstIP').textContent = alert.destIP;
    document.getElementById('detailPorts').textContent = alert.ports || '-';
    document.getElementById('detailDescription').textContent = alert.description;
    document.getElementById('detailRecommendation').textContent = alert.recommendation;

    // Status select
    document.getElementById('detailStatusSelect').value = alert.status;

    // Score ring
    const circumference = 2 * Math.PI * 52;
    document.getElementById('scoreRingFg').style.strokeDashoffset = circumference * (1 - alert.severityScore / 10);
    document.getElementById('scoreRingFg').style.stroke = SOCData.getScoreColor(alert.severityScore);
    document.getElementById('detailScore').textContent = alert.severityScore.toFixed(1);
    document.getElementById('detailScore').style.color = SOCData.getScoreColor(alert.severityScore);

    // Score breakdown
    const breakdown = document.getElementById('scoreBreakdown');
    breakdown.innerHTML = Object.values(alert.factors || {}).map(f => `
      <div class="score-factor">
        <span class="factor-name">${f.label}</span>
        <div class="factor-track">
          <div class="factor-fill" style="width:${f.value * 10}%; background:${f.value >= 8 ? 'var(--sev-critical)' : f.value >= 6 ? 'var(--sev-high)' : f.value >= 4 ? 'var(--sev-medium)' : 'var(--accent)'}"></div>
        </div>
        <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">${f.value.toFixed(1)} × ${f.weight}</span>
      </div>
    `).join('');

    // Dedup info
    const dedupInfo = document.getElementById('detailDedupInfo');
    if (alert.isDuplicate) {
      dedupInfo.innerHTML = `
        <span class="dedup-badge duplicate">Duplicate</span>
        <span class="dedup-text">Duplicate of ${alert.duplicateOf}</span>`;
    } else if (alert.dupCount > 0) {
      dedupInfo.innerHTML = `
        <span class="dedup-badge unique">${alert.dupCount + 1} Merged Alerts</span>
        <span class="dedup-text">This alert has absorbed ${alert.dupCount} duplicate(s)</span>`;
    } else {
      dedupInfo.innerHTML = `
        <span class="dedup-badge unique">Unique Alert</span>
        <span class="dedup-text">No duplicates detected</span>`;
    }

    // Dedup history
    const history = document.getElementById('dedupHistory');
    if (alert.dupCount > 0 || alert.isDuplicate) {
      const group = alert.dedupGroup;
      const members = state.allAlerts.filter(a => a.dedupGroup === group);
      history.innerHTML = members.slice(0, 6).map(m => `
        <div class="dedup-history-item">
          <span>${escHTML(m.id)} <span class="mono" style="color:var(--text-muted)">${m.dataSource}</span></span>
          <span class="h-time">${escHTML(m.timestamp.substring(11, 19))} UTC</span>
        </div>
      `).join('');
    } else {
      history.innerHTML = '';
    }

    // Factors full list
    const factorList = document.getElementById('factorList');
    factorList.innerHTML = Object.values(alert.factors || {}).map((f, i) => {
      const icons = ['🎯', '🛡️', '💻', '⏱️', '🔍'];
      return `<div class="factor-item">
        <span class="f-name"><span class="factor-icon">${icons[i]}</span>${f.label} — ${f.note}</span>
        <span class="f-points">${f.value.toFixed(1)} pts (${Math.round(f.value * f.weight * 10) / 10} wtd)</span>
      </div>`;
    }).join('');
  }

  function markAsDuplicate() {
    if (!state.selectedAlert) return;
    state.selectedAlert.isDuplicate = true;
    state.selectedAlert.status = 'Duplicate';
    // Find a potential original to link to (same group or older alert)
    state.selectedAlert.duplicateOf = state.selectedAlert.dedupGroup
      ? state.allAlerts.find(a => a.dedupGroup === state.selectedAlert.dedupGroup && !a.isDuplicate && a.id !== state.selectedAlert.id)?.id || null
      : null;
    showToast('Alert marked', 'Alert ' + state.selectedAlert.id + ' marked as duplicate', 'success');
    closeDetail();
    applyFilters();
  }

  /* ---------- Pagination ---------- */
  function changePage(delta) {
    const newPage = state.pagination.currentPage + delta;
    if (newPage < 1 || newPage > state.pagination.totalPages) return;
    state.pagination.currentPage = newPage;
    renderTable();
  }

  /* ---------- Filters reset ---------- */
  function resetFilters() {
    state.filters.severity = ['Critical', 'High', 'Medium', 'Low', 'Info'];
    state.filters.sources = ['Suricata', 'CrowdStrike', 'Splunk', 'Windows Defender', 'AWS CloudTrail', 'Zeek'];
    state.filters.statuses = ['New', 'Investigating', 'Resolved', 'False Positive'];
    state.filters.timeRange = 'all';
    state.filters.searchText = '';
    state.filters.showDuplicates = false;
    state.filters.minScore = 0;
    state.view = 'merged';

    // Reset UI controls
    document.querySelectorAll('#severityFilter .chip').forEach(c => c.classList.add('active'));
    document.querySelectorAll('.chip-status').forEach(c => c.classList.add('active'));
    document.querySelectorAll('.source-cb').forEach(c => c.checked = true);
    el.globalSearch.value = '';
    el.timeRangeFilter.value = 'all';
    el.minScoreFilter.value = 0;
    el.minScoreLabel.textContent = '0.0';
    el.showDuplicatesToggle.checked = false;
    el.autoMergeToggle.checked = true;
    state.filters.autoMerge = true;

    document.querySelectorAll('.view-btn').forEach(b => {
      const on = b.dataset.view === 'merged';
      b.classList.toggle('active', on);
    });

    applyFilters();
    showToast('Filters cleared', 'Showing all alerts', 'info');
  }

  /* ---------- Report generation & download ---------- */
  function openReportModal() {
    document.getElementById('reportModal').style.display = 'flex';
  }

  function downloadReport(options) {
    const reportData = SOCReport.generateReport(state.filteredAlerts, options);
    downloadBlob(reportData.html, reportData.filename, 'text/html');
    document.getElementById('reportModal').style.display = 'none';
    showToast('Report generated', 'Downloaded ' + reportData.filename, 'success');
  }

  function refreshData() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('refreshing');
    setTimeout(() => {
      state.allAlerts = SOCData.refreshAlerts();
      state.alerts = state.allAlerts.slice();
      applyFilters();
      showToast('Data refreshed', 'Alert dataset regenerated with new findings', 'success');
      btn.classList.remove('refreshing');
    }, 400);
  }

  /* ---------- Toasts ---------- */
  function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = {
      success: '<svg xmlns="http://www.w3.org/2000/svg" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg xmlns="http://www.w3.org/2000/svg" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      info: '<svg xmlns="http://www.w3.org/2000/svg" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `${icons[type] || icons.info}<div><strong>${escHTML(title)}</strong><br><span style="color:var(--text-muted);font-size:12px">${escHTML(message)}</span></div>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 350);
    }, 3500);
  }

  function toggleKbdModal() {
    const modal = document.getElementById('kbdModal');
    modal.style.display = modal.style.display === 'none' ? 'flex' : 'none';
  }

  /* ---------- Utilities ---------- */
  function debounce(fn, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function escHTML(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function downloadBlob(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  /* ---------- Public API ---------- */
  return {
    init,
    openDetail,
    closeDetail,
    showToast,
    downloadReport,
    refreshData
  };
})();

document.addEventListener('DOMContentLoaded', () => {
  SOCApp.init();
});