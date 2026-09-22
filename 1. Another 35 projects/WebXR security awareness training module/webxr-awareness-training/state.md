# State Management Documentation

## Application State Structure

### Root State Object
```javascript
{
  // User Session
  user: {
    id: string,
    startedAt: timestamp,
    completedModules: string[]
  },

  // Training Progress
  training: {
    currentModule: string,
    currentLesson: number,
    modules: {
      [moduleId]: {
        completed: boolean,
        quizScore: number,
        attempts: number,
        lastAccessed: timestamp
      }
    }
  },

  // UI State
  ui: {
    theme: 'dark',
    sidebarOpen: boolean,
    currentView: 'dashboard' | 'lesson' | 'quiz' | 'report',
    notifications: Notification[]
  },

  // Session Data
  session: {
    startTime: timestamp,
    totalTimeSpent: number,
    xpEarned: number,
    achievements: string[]
  }
}
```

### State Persistence

#### localStorage Keys
- `webxr_training_state` - Main application state
- `webxr_training_session` - Current session data
- `webxr_training_settings` - User preferences

#### Save Strategy
- Auto-save on significant actions (module complete, quiz submit)
- Debounced saves for frequent updates (progress %)
- Session recovery on page reload

### State Transitions

#### Starting a Training Session
1. Load persisted state from localStorage
2. Initialize user session if new
3. Restore previous progress
4. Update UI to reflect state

#### Completing a Module
1. Mark module as completed
2. Update quiz scores
3. Award XP/achievements
4. Persist state
5. Show completion notification
6. Update dashboard

#### Generating Report
1. Collect current state
2. Format into HTML template
3. Create downloadable blob
4. Trigger browser download

### State Events

| Event | Trigger | State Changes |
|-------|---------|---------------|
| `MODULE_START` | User begins module | currentModule updated, lastAccessed set |
| `LESSON_COMPLETE` | Lesson finished | Progress updated, XP added |
| `QUIZ_SUBMIT` | Quiz answers submitted | quizScore recorded, attempts incremented |
| `MODULE_COMPLETE` | All lessons done | completed flag set, achievement checked |
| `SESSION_END` | Browser close/tab switch | Session time saved, state persisted |

### Reset/Clear State
- Export state before clearing (for backup)
- Clear all localStorage keys
- Reset UI to initial state
- Redirect to welcome screen
