"""
Streamlit UI for AI Code Assistant.

Architecture:
    UI (Presentation Only) → AssistantPipeline (All Logic)

    • UI: Display, input, user interaction
    • Pipeline: File management, agents, LLM calls, execution
    • Zero business logic in this file

Usage:
    streamlit run src/ui/streamlit_app.py
"""
import streamlit as st
import sys
from pathlib import Path

# Ensure project root is on sys.path for absolute imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import load_config, ConfigError
from src.pipeline import AssistantPipeline, PipelineResult


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="AI Code Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Global font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Dark glassmorphism cards */
    .glass-card {
        background: rgba(30, 30, 46, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
    }

    /* Gradient header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .sub-header {
        color: #a0a0b8;
        font-size: 1rem;
        font-weight: 400;
        margin-bottom: 20px;
    }

    /* Success/Error styling */
    .success-banner {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(16, 185, 129, 0.08));
        border: 1px solid rgba(34, 197, 94, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0;
    }

    .error-banner {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.08));
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0;
    }

    /* File tree styling */
    .file-item {
        padding: 6px 12px;
        border-radius: 8px;
        margin: 2px 0;
        font-size: 0.85rem;
        transition: background 0.2s;
    }
    .file-item:hover { background: rgba(102, 126, 234, 0.12); }

    /* Output terminal */
    .terminal-output {
        background: #1a1b26;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 20px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        color: #c0caf5;
        white-space: pre-wrap;
        max-height: 400px;
        overflow-y: auto;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: rgba(20, 20, 35, 0.95);
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .status-active {
        background: rgba(34, 197, 94, 0.2);
        color: #22c55e;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .status-empty {
        background: rgba(250, 204, 21, 0.2);
        color: #facc15;
        border: 1px solid rgba(250, 204, 21, 0.3);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# BACKEND INITIALIZATION
# ============================================================================

@st.cache_resource
def get_pipeline():
    """Initialize and cache the AssistantPipeline."""
    try:
        config = load_config()
    except ConfigError as e:
        st.error(f"❌ Configuration Error: {e}")
        st.info("💡 Please set the environment variable: `HUGGINGFACE_API_KEY`")
        st.stop()
        return None

    return AssistantPipeline(config)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "pipeline_result": None,
        "selected_file": None,
        "prompt_history": [],
        "active_tab": "assistant",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ============================================================================
# DISPLAY HELPERS
# ============================================================================

def display_pipeline_result(result: PipelineResult):
    """Display pipeline result with styling."""
    if result.success:
        st.markdown(f'<div class="success-banner">{result.message}</div>',
                     unsafe_allow_html=True)

        # Show individual agent results
        for agent_result in result.agent_results:
            if hasattr(agent_result, "output") and agent_result.output:
                with st.expander("📝 Details", expanded=False):
                    st.markdown(agent_result.output)
    else:
        st.markdown(
            f'<div class="error-banner">❌ {result.error}</div>',
            unsafe_allow_html=True,
        )
        for agent_result in result.agent_results:
            err = getattr(agent_result, "error", None)
            if err:
                st.error(err)


def display_file_content(pipeline, file_path: str):
    """Display file content with syntax highlighting."""
    try:
        content = pipeline.read_file(file_path)
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "text"
        lang_map = {"py": "python", "js": "javascript", "json": "json",
                     "md": "markdown", "html": "html", "css": "css",
                     "yaml": "yaml", "yml": "yaml", "txt": "text",
                     "toml": "toml"}
        lang = lang_map.get(ext, ext)
        st.code(content, language=lang)
    except Exception as e:
        st.error(f"Could not read file: {e}")


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">🤖 AI Code Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous code editor powered by Multi-Agent AI</div>',
            unsafe_allow_html=True)

pipeline = get_pipeline()


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### 📁 Project")

    # ---- Project Upload ----
    uploaded_zip = st.file_uploader(
        "Upload project (.zip)",
        type=["zip"],
        key="zip_uploader",
        help="Upload a zip file to load your project into the workspace.",
    )

    if uploaded_zip is not None:
        if st.button("📦 Extract Project", use_container_width=True):
            with st.spinner("Extracting..."):
                try:
                    result = pipeline.upload_project(uploaded_zip.read())
                    st.success(f"✅ Uploaded {result['total_files']} files")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {e}")

    # ---- Clear Workspace ----
    if st.button("🗑️ Clear Workspace", use_container_width=True):
        pipeline.clear_workspace()
        st.session_state.pipeline_result = None
        st.session_state.run_result = None
        st.session_state.selected_file = None
        st.rerun()

    st.divider()

    # ---- File Browser ----
    project_info = pipeline.get_project_info()

    if project_info["has_project"]:
        st.markdown(
            f'<span class="status-badge status-active">'
            f'📂 {project_info["total_files"]} files</span>',
            unsafe_allow_html=True,
        )
        st.markdown("")

        for f in project_info["files"]:
            if st.button(f"📄 {f}", key=f"file_{f}", use_container_width=True):
                st.session_state.selected_file = f
    else:
        st.markdown(
            '<span class="status-badge status-empty">📭 No project loaded</span>',
            unsafe_allow_html=True,
        )
        st.caption("Upload a project or type a prompt to create one.")

    st.divider()

    # ---- System Info ----
    with st.expander("⚙️ System Info"):
        if pipeline:
            status = pipeline.get_system_status()
            st.caption(f"**Model:** {status['model']}")
            st.caption(f"**Agents:** {', '.join(status['agents'].keys())}")
            entry = status.get("entry_point")
            st.caption(f"**Entry point:** {entry or '(auto-detect)'}")

    # ---- Legacy Analysis Tools ----
    with st.expander("🔬 Analysis Tools (Legacy)"):
        st.caption("Analyze code by pasting it below:")
        legacy_code = st.text_area(
            "Code input",
            height=120,
            placeholder="Paste Python code...",
            key="legacy_code",
            label_visibility="collapsed",
        )
        lc1, lc2, lc3 = st.columns(3)

        if lc1.button("🔧 Debug", key="btn_debug"):
            if legacy_code.strip():
                with st.spinner("Debugging..."):
                    r = pipeline.registry.execute("debug", legacy_code)
                    st.session_state.legacy_result = r
                    st.session_state.legacy_title = "🔧 Debug Results"

        if lc2.button("💡 Explain", key="btn_explain"):
            if legacy_code.strip():
                with st.spinner("Explaining..."):
                    r = pipeline.registry.execute("explain", legacy_code)
                    st.session_state.legacy_result = r
                    st.session_state.legacy_title = "💡 Explanation"

        if lc3.button("🧪 Tests", key="btn_tests"):
            if legacy_code.strip():
                with st.spinner("Generating..."):
                    r = pipeline.registry.execute("test", legacy_code)
                    st.session_state.legacy_result = r
                    st.session_state.legacy_title = "🧪 Tests"

        if "legacy_result" in st.session_state and st.session_state.legacy_result:
            result = st.session_state.legacy_result
            st.markdown(f"**{st.session_state.legacy_title}**")
            if isinstance(result, dict):
                st.write(result.get("output", ""))
            elif hasattr(result, "output"):
                if result.success:
                    st.write(result.output)
                else:
                    st.error(result.error)


# ============================================================================
# MAIN AREA
# ============================================================================

# ---- Prompt Input ----
st.markdown("### 💬 What would you like to do?")

prompt_input = st.text_area(
    "Enter your instruction:",
    height=100,
    placeholder=(
        "Examples:\n"
        '• "Create a Flask REST API with user authentication"\n'
        '• "Add error handling to all functions"\n'
        '• "Fix the database connection bug"\n'
        '• "Add unit tests for the utils module"'
    ),
    key="main_prompt",
    label_visibility="collapsed",
)

# ---- Action Buttons ----
col_apply, col_spacer = st.columns([1, 4])

with col_apply:
    btn_apply = st.button(
        "🔨 Apply Changes",
        use_container_width=True,
        type="primary",
        disabled=not prompt_input.strip(),
    )

# ---- Handle Apply Changes ----
if btn_apply and prompt_input.strip():
    with st.spinner("🤖 AI is working on your request..."):
        result = pipeline.process_prompt(prompt_input.strip())
        st.session_state.pipeline_result = result
        st.rerun()

# ---- Display Results ----
st.markdown("---")

# Pipeline result (from Apply Changes)
if st.session_state.pipeline_result:
    st.markdown("### 📝 Changes Applied")
    display_pipeline_result(st.session_state.pipeline_result)

# Execution result (from Run)
# File viewer (from sidebar click)
if st.session_state.selected_file:
    st.markdown(f"### 📄 `{st.session_state.selected_file}`")
    display_file_content(pipeline, st.session_state.selected_file)

# ---- Empty state ----
if (not st.session_state.pipeline_result
    and not st.session_state.selected_file):
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        **📦 Upload a Project**

        Upload a `.zip` file in the sidebar to load your project.
        """)
    with c2:
        st.markdown("""
        **🛠️ Create or Edit**

        Type a prompt above and click **Apply Changes** to modify files.
        """)

# ---- Footer ----
st.markdown("---")
fc1, fc2, fc3 = st.columns(3)
with fc1:
    st.caption("🤖 **Powered by** Multi-Agent AI System")
with fc2:
    st.caption("🧠 **Agents:** Editor, Creator, Debug, Explain, Test")
with fc3:
    st.caption("📂 **Workspace:** file-based project management")
