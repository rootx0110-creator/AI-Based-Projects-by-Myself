# Active Directory Attack Path Visualizer - Memory Documentation

## Overview

This document describes the memory management, data structures, and runtime memory usage of the AD Attack Path Visualizer application.

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Memory                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │              JavaScript Heap (Frontend)              │   │
│  │  • Graph Data Structures                            │   │
│  │  • UI Component State                               │   │
│  │  • vis.js Network Cache                             │   │
│  │  • Event Handlers                                   │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Python Memory (Backend)                 │   │
│  │  • Graph Adjacency List                             │   │
│  │  • Node/Edge Object Cache                           │   │
│  │  • Attack Path Results                              │   │
│  │  • Report Generation Buffer                         │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Session Storage                         │   │
│  │  • User Preferences                                 │   │
│  │  • Filter Settings                                  │   │
│  │  • Recent Searches                                  │   │
│  │  • Viewport State                                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Backend Memory (Python)

### Core Data Structures

```python
# Graph adjacency list representation
graph = {
    'nodes': {
        'node_id': {
            'id': str,
            'type': str,
            'name': str,
            'properties': dict,
            'neighbors': set()  # Adjacent node IDs
        }
    },
    'edges': {
        'edge_id': {
            'id': str,
            'source': str,
            'target': str,
            'type': str,
            'properties': dict
        }
    },
    'adjacency': {
        'node_id': {
            'outgoing': dict(),  # {edge_id: target_id}
            'incoming': dict()   # {edge_id: source_id}
        }
    },
    'indices': {
        'by_type': dict(),      # {type: set(node_ids)}
        'by_name': dict(),      # {name_lower: node_id}
        'by_sid': dict(),       # {sid: node_id}
        'edges_by_type': dict() # {type: set(edge_ids)}
    }
}
```

### Memory Usage Estimates

| Component | Per Item | 1K Nodes | 10K Nodes |
|-----------|----------|----------|-----------|
| Node Object | ~2KB | ~2MB | ~20MB |
| Edge Object | ~0.5KB | ~0.5MB | ~5MB |
| Adjacency List | ~0.1KB | ~0.1MB | ~1MB |
| Index Structures | ~0.2KB | ~0.2MB | ~2MB |
| **Total** | ~2.8KB | ~2.8MB | ~28MB |

### Attack Path Memory

```python
# Attack path result structure
attack_path = {
    'id': str,
    'source': str,
    'target': str,
    'hops': [
        {
            'from': str,
            'to': str,
            'edge_type': str,
            'attack_technique': str,
            'mitre_id': str,
            'description': str
        }
    ],
    'risk_score': float,
    'complexity': str,
    'detection_difficulty': str
}

# Path cache for repeated queries
path_cache = {
    'cache_key': {  # "source_id:target_id"
        'paths': list,
        'timestamp': float,
        'ttl': 300  # 5 minutes
    }
}
```

### Memory Optimization Strategies

1. **String Interning**
```python
# Common strings are interned to save memory
interned_strings = {
    'User': intern('User'),
    'Computer': intern('Computer'),
    'Group': intern('Group'),
    'MemberOf': intern('MemberOf'),
    'AdminTo': intern('AdminTo'),
    # ... etc
}
```

2. **Slot-based Objects**
```python
class Node:
    __slots__ = ['id', 'type', 'name', 'properties']
    
    def __init__(self, id, type, name, properties):
        self.id = id
        self.type = type
        self.name = name
        self.properties = properties
```

3. **Lazy Property Loading**
```python
class LazyNode:
    def __init__(self, id, basic_info):
        self.id = id
        self._basic = basic_info
        self._extended = None
    
    @property
    def extended_properties(self):
        if self._extended is None:
            self._extended = self._load_extended()
        return self._extended
```

## Frontend Memory (JavaScript)

### vis.js Network Cache

```javascript
// vis.js internal data structures
visNetworkCache = {
    nodes: {
        // DataSet with node data
        // ~100 bytes per node overhead
    },
    edges: {
        // DataSet with edge data
        // ~50 bytes per edge overhead
    },
    body: {
        nodes: {
            // Physics body objects
            // ~300 bytes per node
        },
        edges: {
            // Physics body objects
            // ~200 bytes per edge
        }
    }
};
```

### UI State Memory

```javascript
// React component state (if using React)
componentStateMemory = {
    graphComponent: ~50KB,
    sidebarComponent: ~20KB,
    modalComponent: ~10KB,
    reportComponent: ~30KB,
    total: ~110KB
};

// DOM node memory
domMemory = {
    svgElements: 'N * ~2KB',  // N = visible nodes
    canvasMemory: 'viewport_size * 4 bytes',
    eventListeners: '~1KB per listener'
};
```

### Memory Management in JavaScript

```javascript
// WeakMap for node metadata (auto-garbage collected)
const nodeMetadata = new WeakMap();

// LRU Cache for attack paths
class LRUCache {
    constructor(maxSize = 100) {
        this.maxSize = maxSize;
        this.cache = new Map();
    }
    
    get(key) {
        if (this.cache.has(key)) {
            const value = this.cache.get(key);
            this.cache.delete(key);
            this.cache.set(key, value);
            return value;
        }
        return null;
    }
    
    set(key, value) {
        if (this.cache.has(key)) {
            this.cache.delete(key);
        } else if (this.cache.size >= this.maxSize) {
            // Remove oldest entry
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
        this.cache.set(key, value);
    }
}

// Memory monitoring
const memoryMonitor = {
    checkUsage() {
        if (performance.memory) {
            return {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            };
        }
        return null;
    },
    
    checkThreshold(thresholdMB = 500) {
        const usage = this.checkUsage();
        if (usage) {
            const usedMB = usage.used / 1024 / 1024;
            return usedMB > thresholdMB;
        }
        return false;
    }
};
```

## Memory Cleanup

### Backend Cleanup

```python
class MemoryManager:
    def __init__(self, max_nodes=50000, max_paths=1000):
        self.max_nodes = max_nodes
        self.max_paths = max_paths
        self.path_cache = {}
        self.node_cache = {}
    
    def cleanup(self):
        """Perform garbage collection and cache cleanup"""
        import gc
        
        # Clear old path cache entries
        self._expire_cache_entries()
        
        # Run Python garbage collector
        gc.collect()
        
        # Report memory usage
        return self.get_memory_stats()
    
    def _expire_cache_entries(self, ttl=300):
        """Remove cache entries older than TTL"""
        import time
        current_time = time.time()
        expired = [
            key for key, val in self.path_cache.items()
            if current_time - val['timestamp'] > ttl
        ]
        for key in expired:
            del self.path_cache[key]
    
    def get_memory_stats(self):
        """Get current memory statistics"""
        import sys
        return {
            'nodes': len(self.node_cache),
            'paths': len(self.path_cache),
            'estimated_size_mb': sys.getsizeof(self.node_cache) / 1024 / 1024
        }
```

### Frontend Cleanup

```javascript
class MemoryCleaner {
    constructor() {
        this.cleanupInterval = null;
    }
    
    start(intervalMs = 60000) {
        this.cleanupInterval = setInterval(() => {
            this.cleanup();
        }, intervalMs);
    }
    
    stop() {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
        }
    }
    
    cleanup() {
        // Clear unused caches
        this.clearPathCache();
        
        // Force garbage collection hint
        if (window.gc) {
            window.gc();
        }
        
        // Log memory usage
        this.logMemoryUsage();
    }
    
    clearPathCache() {
        // Implementation depends on cache structure
    }
    
    logMemoryUsage() {
        const usage = memoryMonitor.checkUsage();
        if (usage) {
            console.log(`Memory: ${(usage.used / 1024 / 1024).toFixed(2)}MB`);
        }
    }
}
```

## Memory Profiling

### Python Memory Profiler

```python
# Add to requirements: memory_profiler

from memory_profiler import profile

@profile
def analyze_attack_paths(graph, source, target):
    """Profiled attack path analysis"""
    paths = bfs(graph, source, target)
    return paths
```

### Chrome DevTools Memory Profiling

1. Open Chrome DevTools (F12)
2. Go to Memory tab
3. Take heap snapshot before operation
4. Perform operation (e.g., load large graph)
5. Take another heap snapshot
6. Compare snapshots to find memory leaks

### Memory Warning Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Heap Used | >200MB | >400MB |
| Nodes Loaded | >10,000 | >30,000 |
| Edges Loaded | >50,000 | >200,000 |
| Attack Paths | >100 | >500 |
| Cache Size | >1,000 | >5,000 |

## Memory Best Practices

1. **Never Store Full Objects Unnecessarily**
   - Store references, not copies
   - Use object pooling for frequently created objects

2. **Clean Up Event Listeners**
   - Remove listeners when components unmount
   - Use WeakRef for callbacks

3. **Lazy Load Data**
   - Load node details on-demand
   - Paginate large result sets

4. **Use Typed Arrays When Possible**
   - Float32Array for coordinates
   - Uint8Array for node types

5. **Monitor Memory Regularly**
   - Log memory usage periodically
   - Alert on high usage
   - Implement automatic cleanup
