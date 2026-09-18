// AD Attack Path Visualizer - Frontend Application

// Global state
let graph = null;
let nodesDataSet = null;
let edgesDataSet = null;
let allNodes = [];
let allEdges = [];
let selectedNodeId = null;
let selectedSource = null;
let selectedTarget = null;
let lastPathResults = null;

// Node type icons
const NODE_ICONS = {
    'User': 'fa-user',
    'Computer': 'fa-desktop',
    'Group': 'fa-users',
    'OU': 'fa-folder',
    'Domain': 'fa-globe',
    'GPO': 'fa-cog'
};

// Node type colors
const NODE_COLORS = {
    'User': '#4A90D9',
    'Computer': '#50C878',
    'Group': '#FFB347',
    'OU': '#DDA0DD',
    'Domain': '#FF6B6B',
    'GPO': '#87CEEB'
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initGraph();
    initEventListeners();
    loadGraphData();
});

// Initialize vis.js graph
function initGraph() {
    const container = document.getElementById('graphContainer');
    
    nodesDataSet = new vis.DataSet([]);
    edgesDataSet = new vis.DataSet([]);
    
    const options = {
        nodes: {
            shape: 'dot',
            size: 20,
            font: {
                size: 12,
                color: '#f3f4f6',
                face: 'Segoe UI'
            },
            borderWidth: 2,
            shadow: true
        },
        edges: {
            width: 2,
            font: {
                size: 10,
                color: '#9ca3af',
                align: 'middle'
            },
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.5
                }
            },
            smooth: {
                type: 'continuous',
                roundness: 0.5
            }
        },
        physics: {
            enabled: true,
            solver: 'barnesHut',
            barnesHut: {
                gravitationalConstant: -3000,
                centralGravity: 0.3,
                springLength: 200,
                springConstant: 0.04,
                damping: 0.09
            },
            stabilization: {
                iterations: 1000,
                fit: true
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            zoomView: true,
            dragView: true,
            multiselect: false,
            navigationButtons: false
        },
        layout: {
            improvedLayout: true,
            hierarchical: false
        }
    };
    
    graph = new vis.Network(container, { nodes: nodesDataSet, edges: edgesDataSet }, options);
    
    // Event listeners
    graph.on('click', onNodeClick);
    graph.on('hoverNode', onNodeHover);
    graph.on('blurNode', onNodeBlur);
    graph.on('stabilized', onGraphStabilized);
}

// Initialize event listeners
function initEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(function(e) {
        searchNodes(e.target.value);
    }, 300));
    
    // Drag and drop for import
    const uploadArea = document.getElementById('uploadArea');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.style.borderColor = '#3b82f6';
            this.style.background = 'rgba(59, 130, 246, 0.1)';
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.style.borderColor = '';
            this.style.background = '';
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.style.borderColor = '';
            this.style.background = '';
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFile(files[0]);
            }
        });
    }
}

// Load graph data from server
async function loadGraphData() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/graph');
        const data = await response.json();
        
        allNodes = data.nodes;
        allEdges = data.edges;
        
        updateGraph();
        updateStats();
        updateNodeLists();
        updateAnalysisSelects();
        
        showLoading(false);
    } catch (error) {
        console.error('Error loading graph data:', error);
        showNotification('Error loading graph data', 'error');
        showLoading(false);
    }
}

// Update graph visualization
function updateGraph() {
    nodesDataSet.clear();
    edgesDataSet.clear();
    
    // Add nodes with styling
    const styledNodes = allNodes.map(node => ({
        id: node.id,
        label: node.label,
        color: {
            background: node.color,
            border: node.color,
            highlight: {
                background: adjustColor(node.color, 30),
                border: node.color
            },
            hover: {
                background: adjustColor(node.color, 20),
                border: node.color
            }
        },
        group: node.group,
        properties: node.properties
    }));
    
    nodesDataSet.add(styledNodes);
    edgesDataSet.add(allEdges.map(edge => ({
        ...edge,
        originalColor: edge.color
    })));
}

// Update statistics
function updateStats() {
    document.getElementById('totalNodes').textContent = allNodes.length;
    document.getElementById('totalEdges').textContent = allEdges.length;
}

// Update node lists
function updateNodeLists() {
    const container = document.getElementById('nodeListContainer');
    container.innerHTML = '';
    
    // Group nodes by type
    const grouped = {};
    allNodes.forEach(node => {
        if (!grouped[node.group]) {
            grouped[node.group] = [];
        }
        grouped[node.group].push(node);
    });
    
    // Create node items
    Object.keys(grouped).sort().forEach(type => {
        grouped[type].forEach(node => {
            const item = document.createElement('div');
            item.className = 'node-item';
            item.dataset.id = node.id;
            item.onclick = () => selectNode(node.id);
            
            item.innerHTML = `
                <div class="node-icon ${type.toLowerCase()}">
                    <i class="fas ${NODE_ICONS[type] || 'fa-circle'}"></i>
                </div>
                <div class="node-info">
                    <div class="node-name">${escapeHtml(node.label)}</div>
                    <div class="node-type">${type}</div>
                </div>
            `;
            
            container.appendChild(item);
        });
    });
}

// Update analysis selects
function updateAnalysisSelects() {
    const sourceSelect = document.getElementById('sourceNode');
    const targetSelect = document.getElementById('targetNode');
    
    sourceSelect.innerHTML = '<option value="">Select source...</option>';
    targetSelect.innerHTML = '<option value="">Select target...</option>';
    
    // Add nodes grouped by type
    const grouped = {};
    allNodes.forEach(node => {
        if (!grouped[node.group]) {
            grouped[node.group] = [];
        }
        grouped[node.group].push(node);
    });
    
    Object.keys(grouped).sort().forEach(type => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = type;
        
        grouped[type].forEach(node => {
            const option = document.createElement('option');
            option.value = node.id;
            option.textContent = node.label;
            optgroup.appendChild(option);
        });
        
        sourceSelect.appendChild(optgroup.cloneNode(true));
        targetSelect.appendChild(optgroup);
    });
}

// Node click handler
function onNodeClick(params) {
    if (params.nodes.length > 0) {
        selectNode(params.nodes[0]);
    } else {
        deselectNode();
    }
}

// Select node
function selectNode(nodeId) {
    selectedNodeId = nodeId;
    
    // Update node list selection
    document.querySelectorAll('.node-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.id === nodeId);
    });
    
    // Highlight node in graph
    graph.selectNodes([nodeId]);
    
    // Load node details
    loadNodeDetails(nodeId);
    
    // Show right sidebar
    document.getElementById('rightSidebar').classList.add('open');
}

// Deselect node
function deselectNode() {
    selectedNodeId = null;
    
    document.querySelectorAll('.node-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    graph.unselectAll();
    
    document.getElementById('nodeDetails').innerHTML = `
        <div class="empty-state">
            <i class="fas fa-mouse-pointer"></i>
            <p>Click a node to see details</p>
        </div>
    `;
    
    document.getElementById('rightSidebar').classList.remove('open');
}

// Load node details
async function loadNodeDetails(nodeId) {
    try {
        const response = await fetch(`/api/node/${nodeId}`);
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        const node = data.node;
        const connections = data.connections;
        
        const detailsHtml = `
            <div class="detail-card">
                <h4>Node Information</h4>
                <div class="detail-row">
                    <span class="detail-label">Name</span>
                    <span class="detail-value">${escapeHtml(node.name)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Type</span>
                    <span class="detail-value">${node.type}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ID</span>
                    <span class="detail-value" style="font-size: 0.8rem;">${node.id}</span>
                </div>
                ${node.properties.admincount ? '<div class="detail-row"><span class="detail-label">Admin</span><span class="detail-value" style="color: #ef4444;">Yes</span></div>' : ''}
                ${node.properties.hasspn ? '<div class="detail-row"><span class="detail-label">Kerberoastable</span><span class="detail-value" style="color: #f59e0b;">Yes</span></div>' : ''}
                ${node.properties.dontreqpreauth ? '<div class="detail-row"><span class="detail-label">AS-REP Roastable</span><span class="detail-value" style="color: #f59e0b;">Yes</span></div>' : ''}
            </div>
            
            <div class="detail-card">
                <h4>Outgoing Connections (${connections.outgoing.length})</h4>
                ${connections.outgoing.length > 0 ? 
                    connections.outgoing.map(c => `
                        <div class="connection-item" onclick="selectNode('${c.target_id}')">
                            <span class="connection-type">${escapeHtml(c.edge_type)}</span>
                            <span class="connection-name">${escapeHtml(c.target_name)}</span>
                            <span class="node-type">${c.target_type}</span>
                        </div>
                    `).join('') : 
                    '<p style="color: var(--text-muted); font-size: 0.85rem;">No outgoing connections</p>'
                }
            </div>
            
            <div class="detail-card">
                <h4>Incoming Connections (${connections.incoming.length})</h4>
                ${connections.incoming.length > 0 ? 
                    connections.incoming.map(c => `
                        <div class="connection-item" onclick="selectNode('${c.source_id}')">
                            <span class="connection-type">${escapeHtml(c.edge_type)}</span>
                            <span class="connection-name">${escapeHtml(c.source_name)}</span>
                            <span class="node-type">${c.source_type}</span>
                        </div>
                    `).join('') : 
                    '<p style="color: var(--text-muted); font-size: 0.85rem;">No incoming connections</p>'
                }
            </div>
            
            <div style="margin-top: 16px; display: flex; gap: 10px;">
                <button class="btn btn-primary btn-block" onclick="setAsSource('${nodeId}')">
                    <i class="fas fa-arrow-right"></i> Set as Source
                </button>
                <button class="btn btn-accent btn-block" onclick="setAsTarget('${nodeId}')">
                    <i class="fas fa-arrow-left"></i> Set as Target
                </button>
            </div>
        `;
        
        document.getElementById('nodeDetails').innerHTML = detailsHtml;
    } catch (error) {
        console.error('Error loading node details:', error);
        showNotification('Error loading node details', 'error');
    }
}

// Set node as source for path analysis
function setAsSource(nodeId) {
    selectedSource = nodeId;
    document.getElementById('sourceNode').value = nodeId;
    showNotification('Node set as source', 'success');
}

// Set node as target for path analysis
function setAsTarget(nodeId) {
    selectedTarget = nodeId;
    document.getElementById('targetNode').value = nodeId;
    showNotification('Node set as target', 'success');
}

// Find attack paths
async function findAttackPaths() {
    const sourceId = document.getElementById('sourceNode').value;
    const targetId = document.getElementById('targetNode').value;
    
    if (!sourceId || !targetId) {
        showNotification('Please select both source and target nodes', 'warning');
        return;
    }
    
    if (sourceId === targetId) {
        showNotification('Source and target must be different', 'warning');
        return;
    }
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/attack-paths', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: sourceId,
                target: targetId,
                max_paths: 10
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        displayPathResults(data);
        
        showLoading(false);
    } catch (error) {
        console.error('Error finding paths:', error);
        showNotification('Error finding attack paths', 'error');
        showLoading(false);
    }
}

// Display path results
function displayPathResults(data) {
    const container = document.getElementById('pathResults');
    lastPathResults = data;
    
    if (!data.paths || data.paths.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-times-circle"></i>
                <p>No attack paths found</p>
            </div>
        `;
        return;
    }
    
    let html = `<h4 style="margin-bottom: 12px;">Found ${data.paths.length} attack path(s)</h4>`;
    
    data.paths.forEach((path, index) => {
        const riskClass = path.risk_score >= 80 ? 'critical' : 
                         path.risk_score >= 60 ? 'high' : 
                         path.risk_score >= 40 ? 'medium' : 'low';
        
        const nodeNames = path.nodes.map(id => {
            const node = allNodes.find(n => n.id === id);
            return node ? node.label : id;
        });
        
        const edgeTypes = path.edges.map(e => e.type);
        
        html += `
            <div class="path-item risk-${riskClass}" onclick="highlightPath(${index})">
                <div class="path-header">
                    <span class="path-risk ${riskClass}">Risk: ${path.risk_score}</span>
                    <span class="path-length">${path.length} hops</span>
                </div>
                <div class="path-nodes">
                    <strong>Path:</strong> ${nodeNames.join(' → ')}
                </div>
                <div style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
                    <strong>Techniques:</strong> ${[...new Set(edgeTypes)].join(', ')}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Highlight path on graph
function highlightPath(pathIndex) {
    if (!lastPathResults || !lastPathResults.paths[pathIndex]) {
        showNotification('No path to highlight', 'warning');
        return;
    }
    
    const path = lastPathResults.paths[pathIndex];
    const pathNodeIds = new Set(path.nodes);
    const pathEdgeIds = new Set(path.edges.map(e => e.id));
    
    // Reset all nodes and edges
    nodesDataSet.forEach(node => {
        const base = NODE_COLORS[node.group] || '#888';
        const inPath = pathNodeIds.has(node.id);
        nodesDataSet.update({
            id: node.id,
            color: {
                background: inPath ? '#ef4444' : base,
                border: inPath ? '#ef4444' : base
            },
            opacity: inPath ? 1 : 0.2
        });
    });
    
    edgesDataSet.forEach(edge => {
        const inPath = pathEdgeIds.has(edge.id);
        edgesDataSet.update({
            id: edge.id,
            color: {
                color: inPath ? '#ef4444' : (edge.originalColor || '#888'),
                opacity: inPath ? 1 : 0.15
            },
            width: inPath ? 4 : 2
        });
    });
    
    showNotification('Attack path highlighted on graph', 'success');
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.tab-btn').classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName + 'Tab').classList.add('active');
}

// Apply filters
function applyFilters() {
    // Get checked node types
    const nodeTypeFilters = [];
    document.querySelectorAll('#filtersTab .filter-item input[type="checkbox"]').forEach(checkbox => {
        if (checkbox.checked) {
            const type = checkbox.parentElement.textContent.trim();
            nodeTypeFilters.push(type);
        }
    });
    
    // Filter nodes
    const filteredNodeIds = allNodes
        .filter(node => nodeTypeFilters.length === 0 || nodeTypeFilters.includes(node.group))
        .map(node => node.id);
    
    // Filter edges
    const filteredEdgeIds = allEdges
        .filter(edge => filteredNodeIds.includes(edge.from) && filteredNodeIds.includes(edge.to))
        .map(edge => edge.id);
    
    // Update visible nodes and edges
    nodesDataSet.forEach(node => {
        nodesDataSet.update({
            id: node.id,
            hidden: !filteredNodeIds.includes(node.id)
        });
    });
    
    edgesDataSet.forEach(edge => {
        edgesDataSet.update({
            id: edge.id,
            hidden: !filteredEdgeIds.includes(edge.id)
        });
    });
}

// Change graph layout
function changeLayout() {
    const layout = document.getElementById('layoutSelect').value;
    
    if (layout === 'hierarchical') {
        graph.setOptions({
            layout: {
                hierarchical: {
                    direction: 'UD',
                    sortMethod: 'directed'
                }
            }
        });
    } else {
        graph.setOptions({
            layout: {
                hierarchical: false
            },
            physics: {
                enabled: document.getElementById('physicsToggle').checked
            }
        });
    }
}

// Toggle physics
function togglePhysics() {
    const enabled = document.getElementById('physicsToggle').checked;
    graph.setOptions({ physics: { enabled: enabled } });
}

// Reset view
function resetView() {
    graph.fit();
    graph.setOptions({ physics: { enabled: true } });
}

// Search nodes
function searchNodes(query) {
    if (!query) {
        document.querySelectorAll('.node-item').forEach(item => {
            item.style.display = 'flex';
        });
        return;
    }
    
    const lowerQuery = query.toLowerCase();
    document.querySelectorAll('.node-item').forEach(item => {
        const name = item.querySelector('.node-name').textContent.toLowerCase();
        item.style.display = name.includes(lowerQuery) ? 'flex' : 'none';
    });
}

// Load demo data
async function loadDemoData() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/demo');
        const data = await response.json();
        
        if (data.success) {
            await loadGraphData();
            showNotification('Demo data loaded successfully', 'success');
        }
        
        showLoading(false);
    } catch (error) {
        console.error('Error loading demo data:', error);
        showNotification('Error loading demo data', 'error');
        showLoading(false);
    }
}

// Import modal
function showImportModal() {
    document.getElementById('importModal').classList.add('open');
}

// Report modal
function showReportModal() {
    document.getElementById('reportModal').classList.add('open');
}

// Close modal
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('open');
}

// Handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        uploadFile(file);
    }
}

// Upload file
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = progressDiv.querySelector('.progress-fill');
    const progressText = progressDiv.querySelector('.progress-text');
    
    progressDiv.style.display = 'block';
    progressFill.style.width = '50%';
    progressText.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            progressFill.style.width = '100%';
            progressText.textContent = 'Import complete!';
            
            await loadGraphData();
            
            setTimeout(() => {
                closeModal('importModal');
                progressDiv.style.display = 'none';
                progressFill.style.width = '0%';
            }, 1000);
            
            showNotification('Data imported successfully', 'success');
        } else {
            throw new Error(data.error || 'Import failed');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        progressFill.style.width = '0%';
        progressText.textContent = 'Upload failed';
        showNotification('Error importing data', 'error');
    }
}

// Generate report
async function generateReport() {
    const reportType = document.getElementById('reportType').value;
    
    try {
        showLoading(true);
        
        const response = await fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: reportType,
                source: selectedSource,
                target: selectedTarget
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const resultDiv = document.getElementById('reportResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <p>Report generated successfully!</p>
                <p>Size: ${(data.size / 1024).toFixed(2)} KB</p>
                <a href="/api/report/${data.report_id}" target="_blank" class="btn btn-primary" style="margin-top: 10px;">
                    <i class="fas fa-download"></i> Download Report
                </a>
            `;
            
            showNotification('Report generated', 'success');
        }
        
        showLoading(false);
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Error generating report', 'error');
        showLoading(false);
    }
}

// Node hover handler
function onNodeHover(params) {
    document.body.style.cursor = 'pointer';
}

// Node blur handler
function onNodeBlur(params) {
    document.body.style.cursor = 'default';
}

// Graph stabilized handler
function onGraphStabilized(params) {
    console.log('Graph stabilized');
}

// Close right sidebar
function closeSidebar() {
    document.getElementById('rightSidebar').classList.remove('open');
    deselectNode();
}

// Show loading indicator
function showLoading(show) {
    // Implementation depends on UI requirements
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Utility functions
function adjustColor(color, amount) {
    const hex = color.replace('#', '');
    const r = Math.max(0, Math.min(255, parseInt(hex.substr(0, 2), 16) + amount));
    const g = Math.max(0, Math.min(255, parseInt(hex.substr(2, 2), 16) + amount));
    const b = Math.max(0, Math.min(255, parseInt(hex.substr(4, 2), 16) + amount));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add notification styles
const style = document.createElement('style');
style.textContent = `
    .notification {
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 24px;
        background: var(--bg-secondary);
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        z-index: 2000;
        transition: opacity 0.3s ease;
        border: 1px solid var(--border-color);
    }
    .notification-success { border-left: 4px solid #10b981; }
    .notification-error { border-left: 4px solid #ef4444; }
    .notification-warning { border-left: 4px solid #f59e0b; }
    .notification-info { border-left: 4px solid #3b82f6; }
    .notification i {
        font-size: 1.2rem;
    }
    .notification-success i { color: #10b981; }
    .notification-error i { color: #ef4444; }
    .notification-warning i { color: #f59e0b; }
    .notification-info i { color: #3b82f6; }
`;
document.head.appendChild(style);
