# STREAMLIT UI - REFERENCE CARD

## Setup (One Command)
```bash
pip install streamlit
export HUGGINGFACE_API_KEY="your_key"
streamlit run streamlit_app.py
```

## UI Layout
```
┌─────────────────────────────────────┐
│ Developer Assistant                 │
├─────────────────┬───────────────────┤
│                 │                   │
│  CODE EDITOR    │  BUTTONS          │
│  (left)         │  (right)          │
│                 │  💡 Explain       │
│  [code here]    │  🔧 Fix           │
│                 │  🧪 Generate      │
│                 │  📊 Analyze       │
├─────────────────┴───────────────────┤
│ RESULTS (below)                     │
│ [Output displayed here]             │
└─────────────────────────────────────┘
```

## Buttons & What They Do

| 💡 Explain | → `system.explain_code()`  |
| 🔧 Fix | → `system.debug_code()`  |
| 🧪 Tests | → `system.generate_tests()`  |
| 📊 Analyze | → `system.analyze_code()`  |

## File Overview
```
streamlit_app.py (300+ lines)
├─ Imports: main.py, base_agent
├─ Page config: Title, layout, styling
├─ Session state: code_input, last_result
├─ get_system(): Create/cache backend
├─ UI sections: Header, sidebar, editor
├─ Buttons: 4 action buttons
└─ Handlers: Display functions

NO LOGIC IN THIS FILE! All in main.py
```

## Architecture (Key Principle)
```
User → Streamlit UI → Backend (main.py) → Result
        (display)    (all logic)
        
Never:
✗ Analyze code in streamlit_app.py
✗ Call LLM in streamlit_app.py
✗ Manage agents in streamlit_app.py
✗ Route events in streamlit_app.py

Only:
✓ Collect input
✓ Call backend method
✓ Display result
```

## Data Flow Example

```
User enters: "def hello(): pass"
Click: "💡 Explain"
     ↓
UI: code_input = "def hello(): pass"
UI: system = get_system()  [From cache]
UI: result = system.explain_code(code_input)
     ↓
Backend processes (main.py does all work)
     ↓
Backend returns: 
  AgentResult(
    success=True,
    output="This function...",
    metadata={...}
  )
     ↓
UI: display_result(result, "Code Explanation")
     ↓
Browser shows green box with explanation
```

## Common Tasks

### Explain Code
```
Paste code → Click 💡 Explain → Read explanation
```

### Fix Bugs
```
Paste code → Click 🔧 Fix → See bug report
```

### Generate Tests
```
Paste code → Click 🧪 Tests → Copy test code
```

### Analyze Code
```
Paste code → Click 📊 Analyze → See metrics
```

## Configuration

Edit these in `streamlit_app.py`:
```python
config = SystemConfig(
    llm_max_retries=3,         # How many retries
    memory_max_history=100,    # Memory size
    enable_trigger_logging=True,
    enable_async_execution=False
)
```

## Performance

First request:
- ~30s (LLM initialization)

Subsequent requests:
- ~10s (LLM call only, system cached)

Why: `@st.cache_resource` decorator caches system

## Error Messages

| Error | Solution |
|-------|----------|
| "API key not set" | `export HUGGINGFACE_API_KEY="..."` |
| "Module not found" | `pip install streamlit` |
| "Connection error" | Check internet, VPN |
| "Button not responding" | Enter code first |

## Commands/Shortcuts

| Command | Action |
|---------|--------|
| `streamlit run streamlit_app.py` | Start app |
| `Ctrl+C` | Stop app |
| Browser refresh (F5) | Refresh app |
| `R` in terminal | Rerun app |

## Deployment

### Local
```bash
streamlit run streamlit_app.py
```

### Docker
```bash
docker build -t myapp .
docker run -p 8501:8501 myapp
```

### Streamlit Cloud
```bash
# Push to GitHub → Deploy on share.streamlit.io
```

## Documentation Files

| File | Read For |
|------|----------|
| [STREAMLIT_QUICK_START.md](STREAMLIT_QUICK_START.md) | Quick overview (5 min) |
| [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md) | Complete guide (20 min) |
| [STREAMLIT_ARCHITECTURE.md](STREAMLIT_ARCHITECTURE.md) | Visual diagrams (15 min) |
| [STREAMLIT_SUMMARY.md](STREAMLIT_SUMMARY.md) | Full summary (10 min) |

## Code Structure

```python
# Pattern for all buttons:

if button_name:
    with st.spinner("..."):               # Show loading
        try:
            result = system.method(code)   # Call backend
            display_result(result, title)  # Show result
        except Exception as e:
            st.error(f"Error: {e}")        # Show error
```

## Best Practices

✅ DO
- Paste code in editor
- Click buttons and wait
- Check sidebar for system status
- Read documentation
- Report issues

❌ DON'T
- Add logic to UI
- Call analysis functions from UI
- Call LLM from UI
- Bypass backend methods
- Modify core behavior

## Key Files
```
streamlit_app.py        ← Start here
main.py                 ← Backend logic
base_agent.py          ← Result type
All other modules       ← Used by main.py
```

## System Status

Sidebar shows:
- Number of agents (4)
- Memory entries
- Agent names and roles
- System dependencies

## Help

**Quick help**: Read [STREAMLIT_QUICK_START.md](STREAMLIT_QUICK_START.md)
**Full help**: Read [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md)
**Architecture**: Read [STREAMLIT_ARCHITECTURE.md](STREAMLIT_ARCHITECTURE.md)

## One-Liner Start

```bash
pip install streamlit && export HUGGINGFACE_API_KEY="..." && streamlit run streamlit_app.py
```

## Next Steps

1. ✅ Install Streamlit
2. ✅ Set API key
3. ✅ Run app
4. ✅ Try buttons
5. ✅ Read guides
6. ✅ Extend system
7. ✅ Deploy

---

**Status**: ✅ Ready to Use
**Quality**: ✅ Production Ready
**Logic Separation**: ✅ Enforced
