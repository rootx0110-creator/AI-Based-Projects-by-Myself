# Active Directory Attack Path Visualizer - State Documentation

## Application State Overview

This document describes the various states and data structures used by the AD Attack Path Visualizer application.

## Global Application State

```javascript
AppState = {
    // Graph visualization state
    graph: {
        nodes: [],              // Array of AD object nodes
        edges: [],              // Array of relationships/edges
        selectedNode: null,     // Currently selected node
        hoveredNode: null,      // Currently hovered node
        zoom: 1.0,              // Current zoom level
        pan: { x: 0, y: 0 },   // Current pan position
        layout: 'force',        // Current layout algorithm
        filter: {
            nodeTypes: [],      // Active node type filters
            edgeTypes: [],      // Active edge type filters
            searchText: ''      // Current search filter
        }
    },
    
    // Attack path analysis state
    analysis: {
        sourceNode: null,       // Attack source node
        targetNode: null,       // Attack target node
        paths: [],              // Found attack paths
        selectedPath: null,     // Currently displayed path
        isAnalyzing: false      // Analysis in progress flag
    },
    
    // UI state
    ui: {
        sidebarOpen: true,      // Sidebar visibility
        activeTab: 'graph',     // Active sidebar tab
        modalOpen: false,       // Modal dialog state
        notifications: [],      // Active notifications
        theme: 'dark'           // UI theme (dark/light)
    },
    
    // Data import/export state
    data: {
        isImporting: false,     // Import in progress
        importProgress: 0,      // Import progress percentage
        lastImport: null,       // Last import timestamp
        reports: []             // Generated reports list
    }
};
```

## Node State Structure

```javascript
NodeState = {
    id: 'string',               // Unique node identifier
    type: 'string',             // Node type (User, Computer, Group, etc.)
    name: 'string',             // Display name
    properties: {
        // Common properties
        objectid: 'string',     // AD object ID (SID)
        domain: 'string',       // Domain name
        distinguishedname: 'string', // DN
        
        // Type-specific properties
        enabled: 'boolean',     // Account enabled (Users/Computers)
        admincount: 'boolean',  // Admin count flag
        hasspn: 'boolean',      // Has SPN (Kerberoastable)
        dontreqpreauth: 'boolean', // No preauth (AS-REP Roastable)
        pwdlastset: 'number',   // Password last set timestamp
        lastlogon: 'number',    // Last logon timestamp
        operatingsystem: 'string', // OS (Computers)
        description: 'string',  // Description
        
        // Group properties
        membercount: 'number',  // Number of members
        
        // Computed properties
        inboundEdges: 'number', // Number of incoming edges
        outboundEdges: 'number', // Number of outgoing edges
        riskScore: 'number',    // Computed risk score
        attackPaths: 'number'   // Number of attack paths through node
    },
    state: {
        selected: 'boolean',    // Is node selected
        highlighted: 'boolean', // Is node highlighted
        expanded: 'boolean',    // Is node expanded in sidebar
        marked: 'boolean',      // Is node marked for analysis
        color: 'string',        // Node color override
        size: 'number'          // Node size override
    }
};
```

## Edge State Structure

```javascript
EdgeState = {
    id: 'string',               // Unique edge identifier
    source: 'string',           // Source node ID
    target: 'string',           // Target node ID
    type: 'string',             // Edge type
    properties: {
        isACL: 'boolean',       // Is ACL-based relationship
        isACLPath: 'boolean',   // Is part of ACL chain
        attackCategory: 'string', // Attack category
        description: 'string',  // Human-readable description
        riskLevel: 'string'     // Risk level (low/medium/high/critical)
    },
    state: {
        selected: 'boolean',    // Is edge selected
        highlighted: 'boolean', // Is edge highlighted
        visible: 'boolean',     // Is edge visible
        weight: 'number'        // Edge weight for visualization
    }
};
```

## Attack Path State

```javascript
AttackPathState = {
    id: 'string',               // Unique path identifier
    source: 'string',           // Source node ID
    target: 'string',           // Target node ID
    nodes: ['string'],          // Ordered list of node IDs
    edges: ['string'],          // Ordered list of edge IDs
    riskLevel: 'string',        // Overall risk level
    attackTypes: ['string'],    // Types of attacks in path
    description: 'string',      // Human-readable description
    metrics: {
        length: 'number',       // Path length
        complexity: 'string',   // Attack complexity
        stealth: 'string',      // Stealth level
        impact: 'string'        // Impact level
    },
    state: {
        selected: 'boolean',    // Is path selected
        highlighted: 'boolean', // Is path highlighted
        animated: 'boolean'     // Is path animation active
    }
};
```

## UI Component States

### Sidebar State
```javascript
SidebarState = {
    activeTab: 'string',        // 'graph' | 'analysis' | 'reports' | 'settings'
    width: 'number',            // Sidebar width in pixels
    sections: {
        nodeList: {
            expanded: 'boolean',
            sortBy: 'string',   // 'name' | 'type' | 'risk'
            groupBy: 'string'   // 'none' | 'type' | 'domain'
        },
        details: {
            nodeId: 'string',   // Node being inspected
            tab: 'string'       // 'overview' | 'properties' | 'paths'
        }
    }
};
```

### Graph Visualization State
```javascript
GraphViewState = {
    viewport: {
        x: 'number',           // Viewport X position
        y: 'number',           // Viewport Y position
        width: 'number',       // Viewport width
        height: 'number',      // Viewport height
        zoom: 'number'         // Zoom level (0.1 - 3.0)
    },
    physics: {
        enabled: 'boolean',    // Physics simulation enabled
        solver: 'string',      // 'barnesHut' | 'forceAtlas2'
        stabilization: {
            iterations: 'number',
            fit: 'boolean'
        }
    },
    interaction: {
        dragNodes: 'boolean',
        dragView: 'boolean',
        zoomView: 'boolean',
        hover: 'boolean',
        tooltipDelay: 'number'
    },
    nodes: {
        shape: 'string',       // 'dot' | 'diamond' | 'square' | 'triangle'
        font: {
            size: 'number',
            color: 'string',
            face: 'string'
        },
        scaling: {
            min: 'number',
            max: 'number'
        }
    },
    edges: {
        smooth: 'boolean',
        arrows: 'string',      // 'to' | 'from' | 'middle' | 'none'
        color: {
            color: 'string',
            highlight: 'string',
            hover: 'string'
        }
    }
};
```

## Filter State

```javascript
FilterState = {
    nodeTypes: {
        User: 'boolean',
        Computer: 'boolean',
        Group: 'boolean',
        OU: 'boolean',
        Domain: 'boolean',
        GPO: 'boolean'
    },
    edgeTypes: {
        MemberOf: 'boolean',
        AdminTo: 'boolean',
        HasSession: 'boolean',
        CanRDP: 'boolean',
        CanPSRemote: 'boolean',
        ExecuteDCOM: 'boolean',
        SQLAdmin: 'boolean',
        AllowedToDelegate: 'boolean',
        AllowedToAct: 'boolean',
        ForceChangePassword: 'boolean',
        AddKeyCredentialLink: 'boolean',
        WriteDACL: 'boolean',
        WriteOwner: 'boolean',
        GenericAll: 'boolean',
        GenericWrite: 'boolean',
        Owns: 'boolean',
        ReadLAPSPassword: 'boolean',
        ReadGMSAPassword: 'boolean'
    },
    properties: {
        enabled: 'boolean',
        adminCount: 'boolean',
        hasSPN: 'boolean',
        noPreAuth: 'boolean',
        inactiveDays: 'number'  // Filter by inactive days
    },
    search: {
        text: 'string',
        regex: 'boolean',
        caseSensitive: 'boolean'
    }
};
```

## Report State

```javascript
ReportState = {
    id: 'string',               // Report ID
    name: 'string',             // Report name
    type: 'string',             // 'full' | 'summary' | 'paths' | 'custom'
    format: 'html',             // Output format
    status: 'string',           // 'pending' | 'generating' | 'complete' | 'error'
    options: {
        includeGraph: 'boolean',
        includePaths: 'boolean',
        includeStats: 'boolean',
        includeRecommendations: 'boolean',
        graphLayout: 'string',
        colorScheme: 'string'
    },
    result: {
        filePath: 'string',     // Generated file path
        fileSize: 'number',     // File size in bytes
        generatedAt: 'string',  // ISO timestamp
        pathCount: 'number',    // Number of paths included
        nodeCount: 'number'     // Number of nodes included
    }
};
```

## Session State Persistence

The application stores minimal state in browser localStorage:

```javascript
// Persisted settings
localStorage.setItem('ad-visualizer-settings', JSON.stringify({
    theme: 'dark',
    graphLayout: 'force',
    sidebarWidth: 300,
    nodeSize: 20,
    edgeWidth: 1,
    physicsEnabled: true,
    showLabels: true,
    colorScheme: 'default'
}));

// Persisted filters
localStorage.setItem('ad-visualizer-filters', JSON.stringify({
    nodeTypes: ['User', 'Computer', 'Group'],
    edgeTypes: ['AdminTo', 'MemberOf', 'HasSession'],
    minRiskScore: 0,
    maxRiskScore: 100
}));
```

## State Transitions

```
┌─────────────┐     Import      ┌─────────────┐
│   Empty     │────────────────▶│   Loaded    │
│   State     │                 │   State     │
└─────────────┘                 └─────────────┘
       │                              │
       │                              │ Select Node
       │                              ▼
       │                        ┌─────────────┐
       │                        │  Selected   │
       │                        │   State     │
       │                        └─────────────┘
       │                              │
       │                              │ Analyze Path
       │                              ▼
       │                        ┌─────────────┐
       │                        │ Analyzing   │
       │                        │   State     │
       │                        └─────────────┘
       │                              │
       │                              │ Complete
       │                              ▼
       │                        ┌─────────────┐
       │                        │  Results    │
       │                        │   State     │
       │                        └─────────────┘
```

## Memory Management

The application uses the following memory management strategies:

1. **Node Caching** - Frequently accessed nodes are cached
2. **Lazy Loading** - Large graphs load nodes on-demand
3. **Virtual Rendering** - Only visible nodes are rendered
4. **Garbage Collection** - Unused objects are cleaned up periodically

### Memory Limits
- Maximum nodes: 50,000
- Maximum edges: 500,000
- Maximum attack paths displayed: 100
- Maximum report size: 10MB
