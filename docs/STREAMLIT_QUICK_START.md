# Streamlit App - Quick Start

## One-Minute Setup

### 1. Install Dependencies
```bash
pip install streamlit
# Streamlit will be in requirements.txt soon
```

### 2. Set API Key
```bash
export HUGGINGFACE_API_KEY="your_huggingface_api_key"
```

### 3. Run App
```bash
streamlit run streamlit_app.py
```

### 4. Use It
- App opens at `http://localhost:8501`
- Paste code in editor
- Click Explain, Fix, Generate Tests, or Analyze
- See results!

---

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Developer Assistant                                    │
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│  CODE EDITOR             │  ACTIONS                     │
│  (Large - left)          │  ✅ Explain                 │
│                          │  ✅ Fix                     │
│  [Paste code here]       │  ✅ Generate Tests          │
│                          │  ✅ Analyze                 │
│                          │                              │
├──────────────────────────┴──────────────────────────────┤
│  RESULTS (Below)                                        │
│                                                         │
│  [Output displayed here]                               │
│                                                         │
└─────────────────────────────────────────────────────────┘

Sidebar:
├─ System Status
│  ├─ Agents: 4
│  ├─ Memory: X entries
│  └─ Agent List
└─ About
```

---

## Buttons

| Button | Calls | Shows |
|--------|-------|-------|
| **💡 Explain** | `system.explain_code()` | Code explanation |
| **🔧 Fix** | `system.debug_code()` | Bug fixes & suggestions |
| **🧪 Generate Tests** | `system.generate_tests()` | Unit tests (pytest) |
| **📊 Analyze** | `system.analyze_code()` | Functions, classes, issues |

---

## How to Use

### Step 1: Paste Code
```python
def hello(name):
    print(f"Hello {name}")
    
hello("World")
```

### Step 2: Click Action Button

**💡 Explain**
```
Result:
"This function prints a greeting message..."
```

**🔧 Fix**
```
Result:
"No issues found. Code looks good!"
```

**🧪 Generate Tests**
```
Result:
def test_hello(capsys):
    hello("Test")
    captured = capsys.readouterr()
    assert "Hello Test" in captured.out
```

**📊 Analyze**
```
Result:
Functions: 1 (hello)
Classes: 0
Issues: 0
```

### Step 3: See Results
Results display below with formatting.

---

## Features

### Code Editor
- 300 pixel height (adjustable)
- Syntax highlighting (basic)
- Placeholder text for hints
- Supports large code blocks

### Status Sidebar
- System metrics
- Available agents
- Memory usage
- About information

### Results Display
- Color-coded (green = success, red = error)
- Expandable metadata
- Clear formatting
- Multiple result types

### Error Handling
- Empty code → Info message
- Backend error → Error message
- Failures → Try again available

---

## Common Tasks

### Explain Python Code
```
1. Paste: def calculate(x): return x * 2
2. Click: 💡 Explain
3. View: Explanation displays
```

### Fix Bugs
```
1. Paste: Code with syntax error
2. Click: 🔧 Fix
3. View: Bug report and fixes
```

### Generate Tests
```
1. Paste: Function to test
2. Click: 🧪 Generate Tests
3. View: pytest test code
```

### Analyze Code
```
1. Paste: Complex code
2. Click: 📊 Analyze
3. View: Functions, classes, imports, issues
```

---

## Configuration

Default config in `streamlit_app.py`:
```python
SystemConfig(
    llm_max_retries=3,
    memory_max_history=100,
    enable_trigger_logging=True,
    enable_async_execution=False
)
```

To change:
1. Edit `streamlit_app.py`
2. Change `SystemConfig(...)` values
3. Restart app

---

## System Behavior

### On Startup
- Initialize backend system (once)
- Validate API key
- Load agents
- Show status in sidebar
- Ready for input

### On Button Click
- Show loading spinner
- Call backend method
- Display result
- Keep in memory
- Ready for next action

### On Error
- Catch exception
- Display error message
- Remain responsive
- Allow retry

---

## Performance

### Fast Startup
- System cached in Streamlit
- Reused across requests
- ~1-2 seconds total

### Fast Requests
- No redundant initialization
- Direct LLM calls
- ~5-30 seconds per request (LLM speed)

### Low Memory
- Memory limited to 100 entries
- Snapshots limited to 10
- Efficient caching

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Run app (after code changes) |
| `R` | Rerun app |
| `C` | Clear cache |
| `Q` | Quit |

---

## Troubleshooting

### App Won't Start
```
Check:
1. Streamlit installed: pip install streamlit
2. Python version 3.8+
3. API key set: echo $HUGGINGFACE_API_KEY
4. Port available: lsof -i :8501
```

### "Module not found" Error
```
Check:
1. In correct directory: cd miltiagent234
2. All files present: ls main.py
3. Python path includes: sys.path.insert(0, str(Path(__file__).parent))
```

### Button Clicks Not Working
```
Check:
1. Code not empty
2. System initialized (sidebar shows agents)
3. API key valid
4. Browser console for errors (F12)
```

### Slow Responses
```
This is normal:
- First request initializes LLM (~30s)
- Subsequent requests are faster (~10s)
- LLM inference time varies
```

---

## Tips & Tricks

### Tip 1: Start Simple
```python
# Good first test
def add(a, b):
    return a + b
```

### Tip 2: Test Each Button
- Explain button first (fastest)
- Then Fix button
- Then Generate Tests
- Then Analyze

### Tip 3: Use Analyze for Large Code
- Get overview first
- Then Explain/Fix as needed
- Faster than other buttons

### Tip 4: Check Sidebar
- Verify system initialized
- See available agents
- Check memory usage

### Tip 5: Browser Refresh
- If stuck, refresh browser
- Streamlit session preserved
- All data safe

---

## Architecture Summary

```
Streamlit UI
(Pure Presentation)
    ↓
    ├─ Code Input (Text Area)
    │
    ├─ Action Buttons
    │  ├─ Explain → system.explain_code()
    │  ├─ Fix    → system.debug_code()
    │  ├─ Tests  → system.generate_tests()
    │  └─ Analysis → system.analyze_code()
    │
    └─ Result Display
       ├─ Success (green)
       ├─ Error (red)
       └─ Metadata (expandable)

Backend System (main.py)
All logic here
```

---

## File Structure

```
streamlit_app.py
├─ Imports & Setup
├─ Page Configuration
├─ Session State Init
├─ Backend System Init (cached)
├─ Header & Sidebar
├─ Main Interface
│  ├─ Code Editor
│  ├─ Action Buttons
│  └─ Result Display Functions
├─ Button Handlers
│  ├─ Explain Handler
│  ├─ Fix Handler
│  ├─ Tests Handler
│  └─ Analyze Handler
└─ Footer
```

---

## Dependencies

```
Required:
✅ streamlit
✅ Python 3.8+
✅ HUGGINGFACE_API_KEY environment variable

Used from existing:
✅ main.py (backend)
✅ base_agent.py (AgentResult)
✅ All other backend modules
```

---

## Next Steps

1. **Install**: `pip install streamlit`
2. **Setup**: `export HUGGINGFACE_API_KEY="..."`
3. **Run**: `streamlit run streamlit_app.py`
4. **Explore**: Try each button
5. **Read**: [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md) for details

---

## Key Points

- ✅ **No Logic in UI** - All logic in `main.py`
- ✅ **Clean Separation** - UI ← Backend
- ✅ **Easy to Extend** - Add buttons by calling system methods
- ✅ **Easy to Maintain** - Change UI without affecting logic
- ✅ **Ready to Deploy** - Works on Streamlit Cloud

---

**Ready to go!** Run `streamlit run streamlit_app.py` 🚀
