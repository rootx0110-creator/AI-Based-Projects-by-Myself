// ===== MATRIX RAIN BACKGROUND =====
const canvas = document.getElementById('matrixCanvas');
const ctx = canvas.getContext('2d');
let matrixChars = ['ア', 'カ', 'サ', 'タ', 'ナ', 'ハ', 'マ', 'ヤ', 'ラ', 'ワ', 'A', 'B', 'C', 'E', 'F', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '#', '$', '%', '&', '+', '=', '<', '>', 'ƒ', 'ß', 'µ', 'ñ', 'ø', 'å'];
let matrixFontSize = 14;
let matrixColumns = 0;
let matrixDrops = [];

function initMatrix() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    matrixColumns = Math.floor(canvas.width / matrixFontSize);
    matrixDrops = Array(matrixColumns).fill(1);
}

function drawMatrix() {
    ctx.fillStyle = 'rgba(8, 12, 26, 0.08)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#00f0ff';
    ctx.font = matrixFontSize + 'px monospace';
    ctx.globalAlpha = 0.5;

    for (let i = 0; i < matrixDrops.length; i++) {
        const text = matrixChars[Math.floor(Math.random() * matrixChars.length)];
        ctx.fillText(text, i * matrixFontSize, matrixDrops[i] * matrixFontSize);
        if (matrixDrops[i] * matrixFontSize > canvas.height && Math.random() > 0.975) {
            matrixDrops[i] = 0;
        }
        matrixDrops[i]++;
    }
}

setInterval(drawMatrix, 40);
initMatrix();
window.addEventListener('resize', initMatrix);

// ===== ANIMATED COUNTERS =====
function animateCounters() {
    const counters = document.querySelectorAll('.stat-value[data-count]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        const duration = 2000;
        const start = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            counter.textContent = Math.floor(eased * target);
            if (progress < 1) requestAnimationFrame(update);
        }
        requestAnimationFrame(update);
    });
}

animateCounters();

// ===== CHART DATA =====
const attackData = {
    'T1055': { name: 'Process Injection', value: 92, color: '#00f0ff' },
    'T1547': { name: 'Boot/Logon Autostart', value: 81, color: '#00f0ff' },
    'T1136': { name: 'Create Account', value: 45, color: '#00f0ff' },
    'T1053': { name: 'Scheduled Task', value: 67, color: '#00f0ff' },
    'T1486': { name: 'Data Encrypted', value: 100, color: '#00f0ff' },
    'T1490': { name: 'Inhibit Recovery', value: 95, color: '#ff3d71' },
    'T1110': { name: 'Brute Force', value: 60, color: '#9b5cf6' },
    'T1041': { name: 'Exfiltration C2', value: 77, color: '#ff9f43' },
    'T1059': { name: 'PowerShell Exec', value: 83, color: '#9b5cf6' },
    'T1027': { name: 'Obfuscated Files', value: 78, color: '#ff9f43' }
};

let attackChart, memoryChart;

function initCharts() {
    // ATT&CK Chart
    const ctx1 = document.getElementById('attackChart');
    if (ctx1) {
        const labels = Object.values(attackData).map(d => d.name);
        const values = Object.values(attackData).map(d => d.value);
        const colors = Object.values(attackData).map(d => d.color);

        const gradient = ctx1.getContext('2d').createLinearGradient(0, 0, 0, 280);
        gradient.addColorStop(0, 'rgba(0, 240, 255, 0.4)');
        gradient.addColorStop(1, 'rgba(0, 240, 255, 0.02)');

        attackChart = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Tactic Coverage %',
                    data: values,
                    backgroundColor: colors.map(c => {
                        const grad = ctx1.getContext('2d').createLinearGradient(0, 0, 0, 280);
                        grad.addColorStop(0, c + 'cc');
                        grad.addColorStop(1, c + '11');
                        return grad;
                    }),
                    borderColor: colors.map(c => c),
                    borderWidth: 1,
                    borderRadius: 4,
                    maxBarThickness: 36
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(8, 12, 26, 0.9)',
                        borderColor: 'rgba(0, 240, 255, 0.3)',
                        borderWidth: 1,
                        titleColor: '#00f0ff',
                        bodyColor: '#eaf0ff',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: {
                            color: '#8b93ad',
                            font: { size: 11 },
                            maxRotation: 45,
                            minRotation: 0
                        }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#8b93ad', font: { size: 11 } },
                        max: 100
                    }
                }
            }
        });
    }

    // Memory Chart
    const ctx2 = document.getElementById('memoryChart');
    if (ctx2) {
        let memData = Array(24).fill(0).map((_, i) => ({
            x: i * 5,
            y: 40 + Math.sin(i / 2.5) * 15 + Math.random() * 10
        }));

        function generateMemData() {
            memData.push({
                x: (memData.length) * 5,
                y: 40 + Math.sin(memData.length / 2.2) * 18 + Math.random() * 12
            });
            memData.shift();
            return memData;
        }

        memoryChart = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: memData.map(d => d.x + 's'),
                datasets: [{
                    label: 'Memory Usage',
                    data: memData.map(d => d.y),
                    borderColor: '#00f0ff',
                    borderWidth: 2,
                    fill: true,
                    backgroundColor: (context) => {
                        const chart = context.chart;
                        const {ctx, chartArea} = chart;
                        if (!chartArea) return null;
                        const grad = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        grad.addColorStop(0, 'rgba(0, 240, 255, 0.35)');
                        grad.addColorStop(1, 'rgba(0, 240, 255, 0.02)');
                        return grad;
                    },
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    pointHoverBackgroundColor: '#00f0ff',
                    pointHoverBorderColor: '#fff',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 300 },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(8, 12, 26, 0.9)',
                        borderColor: 'rgba(0, 240, 255, 0.3)',
                        borderWidth: 1,
                        titleColor: '#00f0ff',
                        bodyColor: '#eaf0ff'
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#8b93ad', font: { size: 10 }, maxTicksLimit: 10 }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#8b93ad', font: { size: 10 } },
                        min: 20,
                        max: 80,
                        title: { display: true, text: 'MB', color: '#5a6a8a' }
                    }
                }
            }
        });

        setInterval(() => {
            if (memoryChart) {
                memoryChart.data.labels = generateMemData().map(d => d.x + 's');
                memoryChart.data.datasets[0].data = memData.map(d => d.y);
                memoryChart.update('none');
            }
        }, 2000);
    }
}

document.addEventListener('DOMContentLoaded', initCharts);

// ===== SAMPLE DATA =====
const sampleData = [
    { hash: 'e4a5f8c1d9b7423f1a6c8d9e0f1b2c3d4e5f6a7b8', family: 'Conti', size: '1.2 MB', type: 'DLL', detection: 38, status: 'analyzed' },
    { hash: 'b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6', family: 'REvil', size: '846 KB', type: 'EXE', detection: 41, status: 'analyzed' },
    { hash: '9f0e1d2c3b4a59687766554433221100ffeeddcc', family: 'LockBit', size: '2.4 MB', type: 'EXE', detection: 36, status: 'analyzed' },
    { hash: '0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b', family: 'BlackCat', size: '1.8 MB', type: 'DLL', detection: 35, status: 'analyzed' },
    { hash: 'cdef0123456789abcdef0123456789abcdef012345', family: 'Ryuk', size: '640 KB', type: 'MEM', detection: 44, status: 'analyzed' },
    { hash: '112233445566778899aabbccddeeff001122334455', family: 'Darkside', size: '954 KB', type: 'EXE', detection: 39, status: 'analyzed' },
    { hash: 'abcdef1234567890abcdef1234567890abcdef123456', family: 'WannaCry', size: '512 KB', type: 'EXE', detection: 42, status: 'analyzed' },
    { hash: '9988776655443322110099887766554433221100aa', family: 'Petya', size: '1.1 MB', type: 'MBR', detection: 45, status: 'analyzed' }
];

function populateSamplesTable() {
    const tbody = document.getElementById('samplesTableBody');
    if (!tbody) return;

    sampleData.forEach(sample => {
        const row = document.createElement('tr');
        const detClass = sample.detection > 40 ? 'det-high' : 'det-medium';
        const statusClass = sample.status === 'analyzed' ? 'status-analyzed' : 'status-pending';
        const shortHash = sample.hash.substring(0, 8) + '...' + sample.hash.substring(sample.hash.length - 8);

        row.innerHTML = `
            <td class="hash-cell">${shortHash}</td>
            <td>${sample.family}</td>
            <td class="size-cell">${sample.size}</td>
            <td><span class="meta-tag" style="padding:2px 8px;font-size:10px">${sample.type}</span></td>
            <td><span class="detection-badge ${detClass}">${sample.detection} / 45</span></td>
            <td><span class="status-badge ${statusClass}">${sample.status.toUpperCase()}</span></td>
        `;
        tbody.appendChild(row);
    });
}

populateSamplesTable();

// ===== SCAN OVERLAY =====
function startScan() {
    const overlay = document.getElementById('scanProgress');
    const text = overlay.querySelector('.scan-progress-text');
    const messages = [
        'INITIALIZING ANALYSIS ENGINE...',
        'DECOMPILING SAMPLE BINARY...',
        'TRACING API CALLS...',
        'ANALYZING CRYPTOGRAPHIC PRIMITIVES...',
        'MONITORING FILE SYSTEM ACTIVITY...',
        'DETECTING PERSISTENCE MECHANISMS...',
        'CORRELATING IOCs WITH THREAT INTEL...',
        'RENDERING BEHAVIORAL MAP...',
        'ANALYSIS COMPLETE.'
    ];
    let i = 0;
    overlay.classList.add('active');
    const interval = setInterval(() => {
        if (i < messages.length) {
            text.textContent = messages[i++];
        } else {
            clearInterval(interval);
            setTimeout(() => {
                overlay.classList.remove('active');
                showToast('Analysis complete. ' + sampleData.length + ' samples processed.');
            }, 500);
        }
    }, 400);
}

// ===== REPORT DOWNLOAD =====
let currentReportType = 'full';

function selectReportType(type, element) {
    currentReportType = type;
    document.querySelectorAll('.report-option').forEach(opt => opt.classList.remove('selected'));
    element.classList.add('selected');
}

function openModal() {
    document.getElementById('reportModal').classList.add('open');
}

function closeModal() {
    document.getElementById('reportModal').classList.remove('open');
}

function generateReport(type) {
    currentReportType = type || 'full';
    document.querySelectorAll('.report-option').forEach(opt => {
        opt.classList.remove('selected');
        if (opt.getAttribute('onclick').includes(type || 'full')) {
            opt.classList.add('selected');
        }
    });
    openModal();
}

function generateAndDownload() {
    closeModal();
    showToast('Generating report...');
    setTimeout(() => {
        const report = buildHTMLReport(currentReportType);
        const blob = new Blob([report], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const now = new Date();
        const dateStr = now.toISOString().split('T')[0];
        a.href = url;
        a.download = `ransomware-analysis-report_${dateStr}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Report downloaded successfully!');
    }, 500);
}

function buildHTMLReport(type) {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const keyFindings = `
        <div class="finding-grid">
            <div class="finding-card critical">
                <div class="f-icon">!</div>
                <div>
                    <h4>SHADOW COPY DELETION</h4>
                    <p>Observed vssadmin.exe Delete Shadows command executed 14 times within 2 minutes before encryption.</p>
                </div>
            </div>
            <div class="finding-card critical">
                <div class="f-icon">!</div>
                <div>
                    <h4>HYBRID AES-RSA ENCRYPTION</h4>
                    <p>Files encrypted using AES-128-CBC with RSA-2048 key wrapping. Encrypted files received ".encry" extension.</p>
                </div>
            </div>
            <div class="finding-card warning">
                <div class="f-icon">!</div>
                <div>
                    <h4>ANTI-FORENSIC TECHNIQUES</h4>
                    <p>Windows Event Logs cleared via <code>wevtutil.exe cl</code>. Evidence of timeline manipulation detected.</p>
                </div>
            </div>
            <div class="finding-card warning">
                <div class="f-icon">!</div>
                <div>
                    <h4>LATERAL MOVEMENT</h4>
                    <p>RDP brute-force activity observed. Accounts with admin privileges were compromised within 3 hours.</p>
                </div>
            </div>
        </div>
    `;

    const tableRows = sampleData.map(s => `
        <tr>
            <td>${s.hash}</td>
            <td>${s.family}</td>
            <td>${s.size}</td>
            <td>${s.type}</td>
            <td>${s.detection}/45</td>
            <td>${s.status.toUpperCase()}</td>
        </tr>
    `).join('');

    const attackRows = Object.entries(attackData).map(([id, d]) => `  
        <tr>
            <td>${id}</td>
            <td>${d.name}</td>
            <td><div class="bar"><div class="bar-fill" style="width:${d.value}%"></div></div></td>
            <td>${d.value}%</td>
        </tr>
    `).join('');

    const reportTitle = type === 'summary' ? 'Executive Summary' : type === 'technical' ? 'Technical Deep-Dive' : 'Full Analysis Report';

    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ransomware Behavior Analysis Report</title>
<style>
    :root {
        --bg: #080c1a;
        --surface: #0d1326;
        --card: #111b33;
        --border: #1e2d4d;
        --cyan: #00f0ff;
        --blue: #4d7cfe;
        --purple: #9b5cf6;
        --red: #ff3d71;
        --orange: #ff9f43;
        --green: #00e396;
        --text: #e8eefc;
        --muted: #8894ab;
        --dim: #5a6a8a;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Segoe UI', Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
    }
    .report {
        max-width: 900px;
        margin: 0 auto;
        padding: 40px 20px;
    }
    .report-header {
        background: linear-gradient(135deg, var(--surface), #141e3a);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 32px;
        margin-bottom: 28px;
        position: relative;
        overflow: hidden;
    }
    .report-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 3px;
        background: linear-gradient(90deg, var(--cyan), var(--purple));
    }
    .report-header::after {
        content: '';
        position: absolute;
        right: -50px; top: -50px;
        width: 200px; height: 200px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(0, 240, 255, 0.08), transparent 70%);
    }
    .report-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        background: rgba(255, 61, 113, 0.15);
        color: var(--red);
        border: 1px solid rgba(255, 61, 113, 0.3);
        margin-bottom: 14px;
        text-transform: uppercase;
    }
    .report-title {
        font-size: 26px;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .report-title span {
        background: linear-gradient(135deg, var(--cyan), var(--purple));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .report-meta {
        font-size: 13px;
        color: var(--muted);
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .section {
        margin-bottom: 28px;
    }
    .section-title {
        font-family: 'Consolas', monospace;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 2px;
        color: var(--cyan);
        text-transform: uppercase;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-title::before {
        content: '◢';
        color: var(--cyan);
    }
    .meta-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
    }
    .meta-item {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px;
    }
    .meta-item label {
        display: block;
        font-size: 10px;
        color: var(--muted);
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 6px;
        font-family: 'Consolas', monospace;
    }
    .meta-item span {
        font-size: 14px;
        font-weight: 600;
    }
    .meta-item.critical span { color: var(--red); }
    .meta-item.good span { color: var(--green); }
    .finding-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
    }
    .finding-card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
        display: flex;
        gap: 14px;
        align-items: flex-start;
    }
    .finding-card.critical { border-left: 3px solid var(--red); }
    .finding-card.warning { border-left: 3px solid var(--orange); }
    .finding-card .f-icon {
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        flex-shrink: 0;
        font-size: 13px;
    }
    .finding-card.critical .f-icon {
        background: rgba(255, 61, 113, 0.2);
        color: var(--red);
    }
    .finding-card.warning .f-icon {
        background: rgba(255, 159, 67, 0.2);
        color: var(--orange);
    }
    .finding-card h4 {
        font-size: 14px;
        margin-bottom: 4px;
    }
    .finding-card p {
        font-size: 12px;
        color: var(--muted);
    }
    .finding-card code {
        background: rgba(255, 255, 255, 0.08);
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 11px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        background: var(--card);
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    th {
        background: var(--surface);
        padding: 12px 16px;
        text-align: left;
        font-size: 10px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: var(--muted);
        font-family: 'Consolas', monospace;
        border-bottom: 1px solid var(--border);
    }
    td {
        padding: 12px 16px;
        font-size: 12px;
        font-family: 'Consolas', monospace;
        border-bottom: 1px solid rgba(30, 45, 77, 0.4);
    }
    tr:last-child td { border-bottom: none; }
    tr:hover { background: rgba(0, 240, 255, 0.03); }
    .bar {
        height: 6px;
        border-radius: 3px;
        background: rgba(255, 255, 255, 0.06);
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, var(--cyan), var(--purple));
    }
    .summary-box {
        background: linear-gradient(135deg, var(--card), #162040);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .summary-box h3 {
        font-size: 15px;
        margin-bottom: 10px;
        color: var(--cyan);
    }
    .summary-box p {
        font-size: 13px;
        color: var(--muted);
    }
    .indicator-list {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }
    .indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        padding: 8px 12px;
        background: var(--card);
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    .indicator .dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .indicator .dot.critical { background: var(--red); }
    .indicator .dot.warning { background: var(--orange); }
    .indicator .dot.info { background: var(--cyan); }
    .footer {
        text-align: center;
        font-size: 11px;
        color: var(--dim);
        padding: 20px;
        border-top: 1px solid var(--border);
        margin-top: 40px;
        font-family: 'Consolas', monospace;
    }
    @media print {
        body { background: white; color: #111; }
        .report-header, .finding-card, .meta-item, table, .summary-box, .indicator {
            background: #f5f5f5;
            border-color: #ccc;
            color: #333;
        }
        .finding-card p, .finding-card h4 { color: #333; }
        .report-title span { color: #333; -webkit-text-fill-color: #333; }
        .section-title { color: #333; }
        .section-title::before { color: #333; }
        th { background: #eee; color: #555; }
        .footer { color: #666; }
    }
</style>
</head>
<body>
<div class="report">
    <div class="report-header">
        <span class="report-badge">CYBERSECURITY THREAT ANALYSIS</span>
        <h1 class="report-title">Ransomware Behavior <span>Analysis Report</span></h1>
        <div class="report-meta">
            <span>Report Type: <b>${reportTitle}</b></span>
            <span>Date: <b>${dateStr}</b></span>
            <span>Time: <b>${timeStr}</b></span>
            <span>Generated by: <b>CyberForge v2.4.1</b></span>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Executive Summary</div>
        <div class="meta-grid">
            <div class="meta-item critical">
                <label>Threat Level</label>
                <span>CRITICAL (9.5/10)</span>
            </div>
            <div class="meta-item">
                <label>Ransomware Family</label>
                <span>Conti v3.7 / SPECTRE</span>
            </div>
            <div class="meta-item good">
                <label>Samples Analyzed</label>
                <span>${sampleData.length}</span>
            </div>
            <div class="meta-item">
                <label>Current Kill-Chain Stage</label>
                <span>7 / 12 - Encryption</span>
            </div>
            <div class="meta-item good">
                <label>Detection Coverage</label>
                <span>98.3% ATT&CK</span>
            </div>
            <div class="meta-item">
                <label>Analysis Engine</label>
                <span>v7 - Deep Behavioral</span>
            </div>
        </div>
        <div class="summary-box">
            <h3>Analysis Overview</h3>
            <p>The analyzed ransomware samples exhibit sophisticated hybrid encryption capabilities (AES-128-CBC with RSA-2048 wrapping), aggressive anti-forensic measures including Windows Event Log clearing and shadow copy deletion, and adaptive multi-threaded file encryption. The malware achieves full execution lifecycle in 6.2 seconds and begins encryption phase using sparse file selection to maximize impact while minimizing detection.</p>
        </div>
    </div>

    ${type === 'summary' ? `
    <div class="section">
        <div class="section-title">Key Findings</div>
        ${keyFindings}
    </div>
    ` : ''}

    ${type !== 'summary' ? `
    <div class="section">
        <div class="section-title">Critical Findings</div>
        ${keyFindings}
    </div>
    ` : ''}

    ${type !== 'summary' ? `
    <div class="section">
        <div class="section-title">Encryption Pattern Analysis</div>
        <table>
            <thead>
                <tr><th>Pattern</th><th>Technique</th><th>Detection Rate</th><th>Severity</th></tr>
            </thead>
            <tbody>
                <tr><td>Hybrid Encryption</td><td>AES-128-CBC + RSA-2048 key wrapping</td><td><div class="bar"><div class="bar-fill" style="width:92%"></div></div></td><td>91%</td></tr>
                <tr><td>Header Overwrite</td><td>64-byte marker injection at file start</td><td><div class="bar"><div class="bar-fill" style="width:85%"></div></div></td><td>85%</td></tr>
                <tr><td>Sparse Encryption</td><td>4KB interval block selection</td><td><div class="bar"><div class="bar-fill" style="width:78%"></div></div></td><td>88%</td></tr>
                <tr><td>Parallel Processing</td><td>16-thread adaptive CPU scheduling</td><td><div class="bar"><div class="bar-fill" style="width:90%"></div></div></td><td>82%</td></tr>
                <tr><td>Key Persistence</td><td>Encrypted key stored in registry \\HKCU\\EncKey</td><td><div class="bar"><div class="bar-fill" style="width:95%"></div></div></td><td>95%</td></tr>
            </tbody>
        </table>
    </div>
    ` : ''}

    <div class="section">
        <div class="section-title">ATT&CK Technique Coverage</div>
        <table>
            <thead>
                <tr><th>Technique ID</th><th>Name</th><th>Coverage</th><th>Score</th></tr>
            </thead>
            <tbody>
                ${attackRows}
            </tbody>
        </table>
    </div>

    ${type !== 'summary' ? `
    <div class="section">
        <div class="section-title">Sample Repository Analysis</div>
        <table>
            <thead>
                <tr><th>SHA-256 Hash</th><th>Family</th><th>Size</th><th>Type</th><th>Detection</th><th>Status</th></tr>
            </thead>
            <tbody>
                ${tableRows}
            </tbody>
        </table>
    </div>
    ` : ''}

    ${type !== 'summary' ? `
    <div class="section">
        <div class="section-title">Indicators of Compromise (IOC)</div>
        <div class="indicator-list">
            <div class="indicator"><span class="dot critical"></span> vssadmin.exe Delete Shadows /all /quiet</div>
            <div class="indicator"><span class="dot critical"></span> C:\\Windows\\System32\\tasks\\update.exe</div>
            <div class="indicator"><span class="dot critical"></span> HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\Updater</div>
            <div class="indicator"><span class="dot warning"></span> beacon.c2-bd.net:8080</div>
            <div class="indicator"><span class="dot warning"></span> 185.220.101.4:443 (TOR exit)</div>
            <div class="indicator"><span class="dot warning"></span> chcp.com (renamed certutil)</div>
            <div class="indicator"><span class="dot info"></span> w32time.dll.dll (DLL side-loading)</div>
            <div class="indicator"><span class="dot info"></span> spoolsv_old.exe (print spooler abuse)</div>
        </div>
    </div>
    ` : ''}

    <div class="footer">
        <p>Generated by CyberForge Ransomware Analysis Platform v2.4.1</p>
        <p>Sample data sourced from public IOC repositories (MalwareBazaar, VirusTotal)</p>
        <p>&copy; 2026 - For authorized security research purposes only</p>
    </div>
</div>
</body>
</html>`;
}

// ===== TOAST =====
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// ===== SCROLL NAV HIGHLIGHT =====
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-link');

window.addEventListener('scroll', () => {
    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        if (window.scrollY >= sectionTop) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + current) {
            link.classList.add('active');
        }
    });
});

// ===== FILTER CHIPS =====
document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        chip.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
    });
});

// ===== BUTTON WAIT FOR DOM =====
document.addEventListener('DOMContentLoaded', () => {
    const chartBoards = document.querySelectorAll('.board');
});