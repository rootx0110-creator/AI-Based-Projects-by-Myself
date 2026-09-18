"""
Active Directory Attack Path Visualizer - Main Application
A BloodHound-style web application for visualizing AD attack paths in lab environments.
"""

from flask import Flask, render_template, jsonify, request, send_file
import json
import os
import sys
import uuid
import time
import threading
import webbrowser
from datetime import datetime
from collections import defaultdict, deque
import heapq

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['REPORT_FOLDER'] = os.path.join(BASE_DIR, 'reports')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)

# In-memory graph storage
graph_data = {
    'nodes': {},
    'edges': {},
    'adjacency': defaultdict(lambda: {'outgoing': {}, 'incoming': {}}),
    'indices': {
        'by_type': defaultdict(set),
        'by_name': {},
        'by_sid': {},
        'edges_by_type': defaultdict(set)
    }
}

# Attack path cache
path_cache = {}

# Node color scheme
NODE_COLORS = {
    'User': '#4A90D9',
    'Computer': '#50C878',
    'Group': '#FFB347',
    'OU': '#DDA0DD',
    'Domain': '#FF6B6B',
    'GPO': '#87CEEB'
}

# Edge type configurations
EDGE_TYPES = {
    'MemberOf': {'color': '#888888', 'arrows': 'to'},
    'AdminTo': {'color': '#FF0000', 'arrows': 'to'},
    'HasSession': {'color': '#FF6600', 'arrows': 'to'},
    'CanRDP': {'color': '#FF00FF', 'arrows': 'to'},
    'CanPSRemote': {'color': '#CC00FF', 'arrows': 'to'},
    'ExecuteDCOM': {'color': '#9900FF', 'arrows': 'to'},
    'SQLAdmin': {'color': '#6600FF', 'arrows': 'to'},
    'AllowedToDelegate': {'color': '#FF9900', 'arrows': 'to'},
    'AllowedToAct': {'color': '#FF6600', 'arrows': 'to'},
    'ForceChangePassword': {'color': '#FF3300', 'arrows': 'to'},
    'AddKeyCredentialLink': {'color': '#CC3300', 'arrows': 'to'},
    'WriteDACL': {'color': '#993300', 'arrows': 'to'},
    'WriteOwner': {'color': '#663300', 'arrows': 'to'},
    'GenericAll': {'color': '#FF0000', 'arrows': 'to', 'dashes': True},
    'GenericWrite': {'color': '#CC0000', 'arrows': 'to', 'dashes': True},
    'Owns': {'color': '#990000', 'arrows': 'to', 'dashes': True},
    'ReadLAPSPassword': {'color': '#FF6666', 'arrows': 'to'},
    'ReadGMSAPassword': {'color': '#FF9999', 'arrows': 'to'}
}

def clear_graph():
    """Clear all graph data"""
    graph_data['nodes'].clear()
    graph_data['edges'].clear()
    graph_data['adjacency'].clear()
    for idx_type in graph_data['indices'].values():
        if isinstance(idx_type, defaultdict):
            idx_type.clear()
        elif isinstance(idx_type, dict):
            idx_type.clear()

def add_node(node_id, node_type, name, properties=None):
    """Add a node to the graph"""
    if properties is None:
        properties = {}
    
    graph_data['nodes'][node_id] = {
        'id': node_id,
        'type': node_type,
        'name': name,
        'properties': properties
    }
    
    # Update indices
    graph_data['indices']['by_type'][node_type].add(node_id)
    graph_data['indices']['by_name'][name.lower()] = node_id
    if 'objectid' in properties:
        graph_data['indices']['by_sid'][properties['objectid']] = node_id
    
    return node_id

def add_edge(source_id, target_id, edge_type, properties=None):
    """Add an edge to the graph"""
    if properties is None:
        properties = {}
    
    edge_id = f"{source_id}->{target_id}:{edge_type}"
    
    graph_data['edges'][edge_id] = {
        'id': edge_id,
        'source': source_id,
        'target': target_id,
        'type': edge_type,
        'properties': properties
    }
    
    # Update adjacency lists
    graph_data['adjacency'][source_id]['outgoing'][edge_id] = target_id
    graph_data['adjacency'][target_id]['incoming'][edge_id] = source_id
    
    # Update edge type index
    graph_data['indices']['edges_by_type'][edge_type].add(edge_id)
    
    return edge_id

def find_shortest_path(source_id, target_id):
    """Find shortest path using BFS"""
    if source_id not in graph_data['nodes'] or target_id not in graph_data['nodes']:
        return None
    
    visited = {source_id}
    queue = deque([(source_id, [source_id], [])])
    
    while queue:
        current, path, edges = queue.popleft()
        
        if current == target_id:
            return {'nodes': path, 'edges': edges}
        
        # Check outgoing edges
        for edge_id, next_id in graph_data['adjacency'][current]['outgoing'].items():
            if next_id not in visited:
                visited.add(next_id)
                edge = graph_data['edges'][edge_id]
                queue.append((next_id, path + [next_id], edges + [{'id': edge_id, 'type': edge['type']}]))
        
        # Check incoming edges (for reverse traversal)
        for edge_id, prev_id in graph_data['adjacency'][current]['incoming'].items():
            if prev_id not in visited:
                visited.add(prev_id)
                edge = graph_data['edges'][edge_id]
                queue.append((prev_id, path + [prev_id], edges + [{'id': edge_id, 'type': edge['type'], 'reverse': True}]))
    
    return None

def find_all_paths(source_id, target_id, max_depth=10):
    """Find all paths up to max_depth using DFS"""
    if source_id not in graph_data['nodes'] or target_id not in graph_data['nodes']:
        return []
    
    all_paths = []
    visited = {source_id}
    
    def dfs(current, path, edges, depth):
        if depth > max_depth:
            return
        
        if current == target_id:
            all_paths.append({'nodes': list(path), 'edges': list(edges)})
            return
        
        # Check outgoing edges
        for edge_id, next_id in graph_data['adjacency'][current]['outgoing'].items():
            if next_id not in visited:
                visited.add(next_id)
                edge = graph_data['edges'][edge_id]
                path.append(next_id)
                edges.append({'id': edge_id, 'type': edge['type']})
                dfs(next_id, path, edges, depth + 1)
                path.pop()
                edges.pop()
                visited.remove(next_id)
        
        # Check incoming edges
        for edge_id, prev_id in graph_data['adjacency'][current]['incoming'].items():
            if prev_id not in visited:
                visited.add(prev_id)
                edge = graph_data['edges'][edge_id]
                path.append(prev_id)
                edges.append({'id': edge_id, 'type': edge['type'], 'reverse': True})
                dfs(prev_id, path, edges, depth + 1)
                path.pop()
                edges.pop()
                visited.remove(prev_id)
    
    dfs(source_id, [source_id], [], 0)
    return all_paths

def calculate_risk_score(path):
    """Calculate risk score for an attack path"""
    score = 0
    high_risk_edges = {'AdminTo', 'DCSync', 'GenericAll', 'Owns', 'ForceChangePassword'}
    medium_risk_edges = {'CanRDP', 'CanPSRemote', 'ExecuteDCOM', 'SQLAdmin', 'WriteDACL', 'WriteOwner'}
    
    for edge_info in path['edges']:
        edge_type = edge_info['type']
        if edge_type in high_risk_edges:
            score += 30
        elif edge_type in medium_risk_edges:
            score += 20
        else:
            score += 10
    
    # Shorter paths are more dangerous
    path_length = len(path['nodes'])
    if path_length <= 3:
        score += 20
    elif path_length <= 5:
        score += 10
    
    return min(score, 100)

def get_attack_category(edge_type):
    """Get attack category for an edge type"""
    categories = {
        'Credential Access': ['Kerberoasting', 'AS-REP Roasting', 'ReadLAPSPassword', 'ReadGMSAPassword'],
        'Lateral Movement': ['CanRDP', 'CanPSRemote', 'ExecuteDCOM', 'SQLAdmin', 'HasSession'],
        'Privilege Escalation': ['AdminTo', 'GenericAll', 'WriteDACL', 'WriteOwner', 'Owns'],
        'Persistence': ['AllowedToDelegate', 'AllowedToAct', 'AddKeyCredentialLink'],
        'Collection': ['MemberOf', 'GenericWrite']
    }
    
    for category, types in categories.items():
        if edge_type in types:
            return category
    return 'Other'

def generate_demo_data():
    """Generate demo AD environment data"""
    clear_graph()
    
    # Add Domain
    add_node('domain-1', 'Domain', 'lab.local', {
        'objectid': 'S-1-5-21-1234567890-1234567890-1234567890',
        'domain': 'LAB',
        'description': 'Lab Domain'
    })
    
    # Add Domain Controllers
    add_node('dc-1', 'Computer', 'DC01.lab.local', {
        'objectid': 'S-1-5-21-1234567890-1234567890-1234567891',
        'operatingsystem': 'Windows Server 2022',
        'enabled': True,
        'admincount': True
    })
    add_edge('dc-1', 'domain-1', 'MemberOf')
    
    # Add OUs
    ous = [
        ('ou-1', 'OU=Domain Controllers'),
        ('ou-2', 'OU=Users'),
        ('ou-3', 'OU=Computers'),
        ('ou-4', 'OU=Servers'),
        ('ou-5', 'OU=Service Accounts')
    ]
    
    for ou_id, ou_name in ous:
        add_node(ou_id, 'OU', ou_name, {
            'objectid': f'S-1-5-21-1234567890-1234567890-{ou_id.split("-")[1]}',
            'domain': 'LAB'
        })
        add_edge(ou_id, 'domain-1', 'MemberOf')
    
    # Add Security Groups
    groups = [
        ('grp-1', 'Domain Admins', True),
        ('grp-2', 'Enterprise Admins', True),
        ('grp-3', 'Server Admins', True),
        ('grp-4', 'Help Desk', False),
        ('grp-5', 'Domain Users', False),
        ('grp-6', 'Backup Operators', True),
        ('grp-7', 'Account Operators', True),
        ('grp-8', 'Print Operators', False)
    ]
    
    for grp_id, grp_name, admin in groups:
        add_node(grp_id, 'Group', grp_name, {
            'objectid': f'S-1-5-32-{grp_id.split("-")[1]}',
            'admincount': admin,
            'domain': 'LAB',
            'membercount': 0
        })
        add_edge(grp_id, 'domain-1', 'MemberOf')
    
    # Add Users
    users = [
        ('usr-1', 'Administrator', True, True, ['grp-1', 'grp-2']),
        ('usr-2', 'john.smith', True, False, ['grp-3', 'grp-5']),
        ('usr-3', 'jane.doe', True, False, ['grp-4', 'grp-5']),
        ('usr-4', 'svc_sql', True, True, ['grp-3']),
        ('usr-5', 'svc_backup', True, True, ['grp-6']),
        ('usr-6', 'mike.wilson', True, False, ['grp-3', 'grp-5']),
        ('usr-7', 'sarah.connor', True, False, ['grp-4', 'grp-5']),
        ('usr-8', 'test.user', True, False, ['grp-5']),
        ('usr-9', 'svc_iis', True, True, ['grp-3']),
        ('usr-10', 'admin_jane', True, True, ['grp-7', 'grp-1']),
        ('usr-11', 'legacy_svc', True, True, ['grp-8']),
        ('usr-12', 'guest_user', False, False, ['grp-5'])
    ]
    
    for usr_id, usr_name, enabled, admin, groups in users:
        add_node(usr_id, 'User', usr_name, {
            'objectid': f'S-1-5-21-1234567890-1234567890-{usr_id.split("-")[1]}',
            'enabled': enabled,
            'admincount': admin,
            'domain': 'LAB',
            'hasspn': admin,
            'dontreqpreauth': not admin,
            'pwdlastset': int(time.time()) - (86400 * 30 if admin else 86400 * 5)
        })
        add_edge(usr_id, 'ou-2', 'MemberOf')
        for grp_id in groups:
            add_edge(usr_id, grp_id, 'MemberOf')
    
    # Add Computers
    computers = [
        ('pc-1', 'WORKSTATION01', False, ['usr-2', 'usr-8']),
        ('pc-2', 'WORKSTATION02', False, ['usr-3', 'usr-7']),
        ('pc-3', 'WORKSTATION03', False, ['usr-6']),
        ('srv-1', 'WEB01', True, ['usr-9']),
        ('srv-2', 'SQL01', True, ['usr-4']),
        ('srv-3', 'FILE01', True, ['usr-5']),
        ('srv-4', 'APP01', True, ['usr-6']),
        ('srv-5', 'EXCHANGE01', True, ['usr-2'])
    ]
    
    for comp_id, comp_name, is_server, session_users in computers:
        comp_type = 'OU=Servers' if is_server else 'OU=Computers'
        ou_id = 'ou-4' if is_server else 'ou-3'
        
        add_node(comp_id, 'Computer', comp_name + '.lab.local', {
            'objectid': f'S-1-5-21-1234567890-1234567890-{comp_id.split("-")[1]}',
            'enabled': True,
            'admincount': is_server,
            'domain': 'LAB',
            'operatingsystem': 'Windows Server 2022' if is_server else 'Windows 11',
            'trustedfordelegation': is_server
        })
        add_edge(comp_id, ou_id, 'MemberOf')
        
        # Add sessions
        for user_id in session_users:
            add_edge(user_id, comp_id, 'HasSession')
    
    # Add Attack Paths (ACLs and permissions)
    attack_edges = [
        # Admin access
        ('usr-1', 'dc-1', 'AdminTo', 'Direct admin access'),
        ('usr-10', 'dc-1', 'AdminTo', 'Admin access via group'),
        ('usr-4', 'srv-2', 'AdminTo', 'SQL service account'),
        ('usr-5', 'srv-3', 'AdminTo', 'Backup operator access'),
        ('usr-9', 'srv-1', 'AdminTo', 'IIS service account'),
        
        # RDP access
        ('usr-2', 'srv-4', 'CanRDP', 'RDP access for support'),
        ('usr-6', 'srv-5', 'CanRDP', 'Exchange admin access'),
        
        # PS Remote
        ('usr-3', 'pc-1', 'CanPSRemote', 'Help desk access'),
        ('usr-7', 'pc-3', 'CanPSRemote', 'Remote support'),
        
        # DCOM
        ('usr-2', 'srv-1', 'ExecuteDCOM', 'App deployment'),
        
        # Delegation
        ('srv-1', 'dc-1', 'AllowedToDelegate', 'Kerberos delegation'),
        ('srv-4', 'srv-2', 'AllowedToDelegate', 'App to SQL'),
        
        # ACL Abuse
        ('grp-7', 'grp-1', 'GenericAll', 'Account Operators abuse'),
        ('usr-10', 'grp-1', 'WriteDACL', 'Can modify DA group'),
        ('usr-4', 'srv-2', 'GenericAll', 'SQL admin full control'),
        
        # Ownership
        ('usr-1', 'usr-10', 'Owns', 'Account owner'),
        
        # Password reading
        ('usr-2', 'usr-4', 'ReadLAPSPassword', 'LAPS password read'),
        ('usr-6', 'usr-9', 'ReadGMSAPassword', 'GMSA password read'),
        
        # Force password change
        ('grp-4', 'usr-8', 'ForceChangePassword', 'Help desk reset'),
        
        # Key credential
        ('usr-10', 'dc-1', 'AddKeyCredentialLink', 'Shadow credentials')
    ]
    
    for src, tgt, edge_type, desc in attack_edges:
        add_edge(src, tgt, edge_type, {'description': desc})
    
    return {
        'nodes_count': len(graph_data['nodes']),
        'edges_count': len(graph_data['edges'])
    }

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/graph')
def get_graph():
    """Get graph data for visualization"""
    nodes = []
    for node_id, node in graph_data['nodes'].items():
        nodes.append({
            'id': node_id,
            'label': node['name'],
            'group': node['type'],
            'color': NODE_COLORS.get(node['type'], '#888888'),
            'properties': node['properties']
        })
    
    edges = []
    for edge_id, edge in graph_data['edges'].items():
        edge_config = EDGE_TYPES.get(edge['type'], {'color': '#888888', 'arrows': 'to'})
        edges.append({
            'id': edge_id,
            'from': edge['source'],
            'to': edge['target'],
            'label': edge['type'],
            'color': edge_config['color'],
            'arrows': edge_config.get('arrows', 'to'),
            'dashes': edge_config.get('dashes', False),
            'properties': edge['properties']
        })
    
    return jsonify({'nodes': nodes, 'edges': edges})

@app.route('/api/node/<node_id>')
def get_node(node_id):
    """Get node details"""
    if node_id not in graph_data['nodes']:
        return jsonify({'error': 'Node not found'}), 404
    
    node = graph_data['nodes'][node_id]
    
    # Get connections
    outgoing = []
    for edge_id, target_id in graph_data['adjacency'][node_id]['outgoing'].items():
        edge = graph_data['edges'][edge_id]
        target = graph_data['nodes'].get(target_id, {})
        outgoing.append({
            'edge_id': edge_id,
            'edge_type': edge['type'],
            'target_id': target_id,
            'target_name': target.get('name', 'Unknown'),
            'target_type': target.get('type', 'Unknown')
        })
    
    incoming = []
    for edge_id, source_id in graph_data['adjacency'][node_id]['incoming'].items():
        edge = graph_data['edges'][edge_id]
        source = graph_data['nodes'].get(source_id, {})
        incoming.append({
            'edge_id': edge_id,
            'edge_type': edge['type'],
            'source_id': source_id,
            'source_name': source.get('name', 'Unknown'),
            'source_type': source.get('type', 'Unknown')
        })
    
    return jsonify({
        'node': {
            'id': node_id,
            'type': node['type'],
            'name': node['name'],
            'properties': node['properties']
        },
        'connections': {
            'outgoing': outgoing,
            'incoming': incoming
        }
    })

@app.route('/api/attack-paths', methods=['POST'])
def find_attack_paths():
    """Find attack paths between two nodes"""
    data = request.json
    source_id = data.get('source')
    target_id = data.get('target')
    max_paths = data.get('max_paths', 10)
    
    if not source_id or not target_id:
        return jsonify({'error': 'Source and target required'}), 400
    
    if source_id not in graph_data['nodes'] or target_id not in graph_data['nodes']:
        return jsonify({'error': 'Invalid node IDs'}), 400
    
    # Check cache
    cache_key = f"{source_id}:{target_id}"
    if cache_key in path_cache:
        cached = path_cache[cache_key]
        if time.time() - cached['timestamp'] < 300:  # 5 min cache
            return jsonify(cached['data'])
    
    # Find paths
    all_paths = find_all_paths(source_id, target_id, max_depth=8)
    
    # Calculate risk scores and sort
    for path in all_paths:
        path['risk_score'] = calculate_risk_score(path)
        path['length'] = len(path['nodes'])
        path['attack_categories'] = list(set(
            get_attack_category(e['type']) for e in path['edges']
        ))
    
    # Sort by risk score (highest first)
    all_paths.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Limit results
    result_paths = all_paths[:max_paths]
    
    result = {
        'source': source_id,
        'target': target_id,
        'paths': result_paths,
        'total_paths': len(all_paths),
        'shortest_path': all_paths[0] if all_paths else None
    }
    
    # Cache result
    path_cache[cache_key] = {
        'data': result,
        'timestamp': time.time()
    }
    
    return jsonify(result)

@app.route('/api/import', methods=['POST'])
def import_data():
    """Import BloodHound JSON data"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        data = json.load(file)
        clear_graph()
        
        # Parse BloodHound format
        if 'data' in data:
            for item in data['data']:
                node_type = item.get('ObjectType', 'Unknown')
                properties = item.get('Properties', {})
                node_id = properties.get('objectid', str(uuid.uuid4()))
                name = properties.get('name', 'Unknown')
                
                add_node(node_id, node_type, name, properties)
        
        return jsonify({
            'success': True,
            'nodes_count': len(graph_data['nodes']),
            'edges_count': len(graph_data['edges'])
        })
    
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo')
def load_demo():
    """Load demo data"""
    stats = generate_demo_data()
    return jsonify({
        'success': True,
        'message': 'Demo data loaded',
        'stats': stats
    })

@app.route('/api/stats')
def get_stats():
    """Get graph statistics"""
    stats = {
        'total_nodes': len(graph_data['nodes']),
        'total_edges': len(graph_data['edges']),
        'nodes_by_type': {},
        'edges_by_type': {},
        'high_risk_nodes': []
    }
    
    for node_type, node_ids in graph_data['indices']['by_type'].items():
        stats['nodes_by_type'][node_type] = len(node_ids)
    
    for edge_type, edge_ids in graph_data['indices']['edges_by_type'].items():
        stats['edges_by_type'][edge_type] = len(edge_ids)
    
    # Find high-risk nodes (many incoming attack edges)
    attack_edge_types = {'AdminTo', 'CanRDP', 'CanPSRemote', 'GenericAll', 'Owns'}
    for node_id in graph_data['nodes']:
        incoming_attacks = sum(
            1 for eid in graph_data['adjacency'][node_id]['incoming']
            if graph_data['edges'][eid]['type'] in attack_edge_types
        )
        if incoming_attacks >= 3:
            node = graph_data['nodes'][node_id]
            stats['high_risk_nodes'].append({
                'id': node_id,
                'name': node['name'],
                'type': node['type'],
                'risk_level': 'critical' if incoming_attacks >= 5 else 'high',
                'attack_count': incoming_attacks
            })
    
    stats['high_risk_nodes'].sort(key=lambda x: x['attack_count'], reverse=True)
    
    return jsonify(stats)

@app.route('/api/search')
def search_nodes():
    """Search nodes by name"""
    query = request.args.get('q', '').lower()
    node_type = request.args.get('type', None)
    
    results = []
    for node_id, node in graph_data['nodes'].items():
        if query in node['name'].lower():
            if node_type is None or node['type'] == node_type:
                results.append({
                    'id': node_id,
                    'name': node['name'],
                    'type': node['type']
                })
    
    return jsonify(results[:50])  # Limit results

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    """Generate HTML report"""
    data = request.json
    report_type = data.get('type', 'full')
    source_id = data.get('source')
    target_id = data.get('target')
    
    report_id = str(uuid.uuid4())[:8]
    report_path = os.path.join(app.config['REPORT_FOLDER'], f'report_{report_id}.html')
    
    # Generate report HTML
    html = generate_html_report(report_type, source_id, target_id)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return jsonify({
        'success': True,
        'report_id': report_id,
        'filename': f'report_{report_id}.html',
        'size': os.path.getsize(report_path)
    })

@app.route('/api/report/<report_id>')
def download_report(report_id):
    """Download generated report"""
    report_path = os.path.join(app.config['REPORT_FOLDER'], f'report_{report_id}.html')
    
    if not os.path.exists(report_path):
        return jsonify({'error': 'Report not found'}), 404
    
    return send_file(report_path, as_attachment=True, download_name=f'report_{report_id}.html')

def generate_html_report(report_type='full', source_id=None, target_id=None):
    """Generate HTML report content"""
    stats = {
        'total_nodes': len(graph_data['nodes']),
        'total_edges': len(graph_data['edges']),
        'nodes_by_type': {t: len(ids) for t, ids in graph_data['indices']['by_type'].items()},
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Find attack paths if source/target provided
    paths_html = ''
    if source_id and target_id:
        paths = find_all_paths(source_id, target_id, max_depth=5)
        for i, path in enumerate(paths[:5], 1):
            risk_score = calculate_risk_score(path)
            risk_class = 'critical' if risk_score >= 80 else 'high' if risk_score >= 60 else 'medium' if risk_score >= 40 else 'low'
            
            path_nodes = []
            for node_id in path['nodes']:
                node = graph_data['nodes'].get(node_id, {})
                path_nodes.append(f"""
                    <div class="path-node">
                        <span class="node-type {node.get('type', '').lower()}">{node.get('type', 'Unknown')}</span>
                        <span class="node-name">{node.get('name', 'Unknown')}</span>
                    </div>
                """)
            
            path_edges = []
            for edge_info in path['edges']:
                path_edges.append(f"""
                    <div class="path-edge">
                        <span class="edge-type">{edge_info['type']}</span>
                    </div>
                """)
            
            paths_html += f"""
            <div class="attack-path">
                <h4>Path {i}</h4>
                <div class="path-metrics">
                    <span class="risk-score {risk_class}">Risk: {risk_score}/100</span>
                    <span class="path-length">Length: {len(path['nodes'])} hops</span>
                </div>
                <div class="path-flow">
                    {''.join(path_nodes)}
                </div>
                <div class="path-edges">
                    {''.join(path_edges)}
                </div>
            </div>
            """
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AD Attack Path Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e0e0e0;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }}
        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            color: #888;
            font-size: 1.1em;
        }}
        .header .generated {{
            color: #666;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #48dbfb;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(72, 219, 251, 0.3);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(72, 219, 251, 0.2);
        }}
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #48dbfb;
            margin-bottom: 5px;
        }}
        .stat-card .label {{
            color: #888;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .type-breakdown {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .type-item {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 15px;
            border-left: 4px solid;
        }}
        .type-item.user {{ border-color: #4A90D9; }}
        .type-item.computer {{ border-color: #50C878; }}
        .type-item.group {{ border-color: #FFB347; }}
        .type-item.ou {{ border-color: #DDA0DD; }}
        .type-item.domain {{ border-color: #FF6B6B; }}
        .attack-path {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .attack-path h4 {{
            color: #feca57;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        .path-metrics {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .risk-score {{
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .risk-score.critical {{ background: #ff6b6b; color: #000; }}
        .risk-score.high {{ background: #ff9f43; color: #000; }}
        .risk-score.medium {{ background: #feca57; color: #000; }}
        .risk-score.low {{ background: #48dbfb; color: #000; }}
        .path-length {{
            color: #888;
            padding: 5px 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
        }}
        .path-flow {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 15px;
        }}
        .path-node {{
            background: rgba(255, 255, 255, 0.1);
            padding: 10px 15px;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .node-type {{
            font-size: 0.7em;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.7;
        }}
        .node-type.user {{ color: #4A90D9; }}
        .node-type.computer {{ color: #50C878; }}
        .node-type.group {{ color: #FFB347; }}
        .node-name {{
            font-weight: bold;
            margin-top: 5px;
        }}
        .path-edges {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .edge-type {{
            background: rgba(255, 107, 107, 0.2);
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.85em;
            color: #ff6b6b;
        }}
        .recommendations {{
            background: rgba(72, 219, 251, 0.1);
            border-radius: 10px;
            padding: 25px;
            border-left: 4px solid #48dbfb;
        }}
        .recommendations h3 {{
            color: #48dbfb;
            margin-bottom: 15px;
        }}
        .recommendations ul {{
            list-style: none;
        }}
        .recommendations li {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .recommendations li:last-child {{
            border-bottom: none;
        }}
        .recommendations li::before {{
            content: "⚠️ ";
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #666;
            font-size: 0.9em;
        }}
        @media print {{
            body {{
                background: white;
                color: #333;
            }}
            .container {{
                box-shadow: none;
                border: 1px solid #ddd;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 AD Attack Path Analysis Report</h1>
            <div class="subtitle">Active Directory Security Assessment</div>
            <div class="generated">Generated: {stats['generated_at']}</div>
        </div>
        
        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="value">{stats['total_nodes']}</div>
                    <div class="label">Total Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="value">{stats['total_edges']}</div>
                    <div class="label">Total Relationships</div>
                </div>
                <div class="stat-card">
                    <div class="value">{stats['nodes_by_type'].get('User', 0)}</div>
                    <div class="label">User Accounts</div>
                </div>
                <div class="stat-card">
                    <div class="value">{stats['nodes_by_type'].get('Computer', 0)}</div>
                    <div class="label">Computer Objects</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔍 Object Breakdown</h2>
            <div class="type-breakdown">
                {''.join(f'<div class="type-item {t.lower()}"><div class="count">{count}</div><div class="type-name">{t}</div></div>' for t, count in stats['nodes_by_type'].items())}
            </div>
        </div>
        
        {"<div class='section'><h2>🎯 Attack Paths</h2>" + paths_html + "</div>" if paths_html else ""}
        
        <div class="section">
            <h2>🛡️ Recommendations</h2>
            <div class="recommendations">
                <h3>Security Remediation</h3>
                <ul>
                    <li>Review and remove unnecessary administrative privileges</li>
                    <li>Implement tiered administration model</li>
                    <li>Audit service account permissions and delegation settings</li>
                    <li>Enable LAPS for local administrator password management</li>
                    <li>Monitor for Kerberoasting and AS-REP Roasting attacks</li>
                    <li>Implement privileged access workstations (PAWs)</li>
                    <li>Regular access reviews and principle of least privilege</li>
                    <li>Enable advanced audit policies for sensitive objects</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>AD Attack Path Visualizer - Security Assessment Report</p>
            <p>This report is for authorized security testing in lab environments only.</p>
        </div>
    </div>
</body>
</html>
"""
    return html

if __name__ == '__main__':
    # Generate demo data on startup
    print("AD Attack Path Visualizer")
    print("=" * 50)
    stats = generate_demo_data()
    print(f"Demo data loaded: {stats['nodes_count']} nodes, {stats['edges_count']} edges")
    print("=" * 50)
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    url = f"http://{host}:{port}"
    print(f"Starting server at {url}")
    print("Press CTRL+C to stop.")
    print("=" * 50)

    if getattr(sys, 'frozen', False):
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(debug=False, host=host, port=port, use_reloader=False)
