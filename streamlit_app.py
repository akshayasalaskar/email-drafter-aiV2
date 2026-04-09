
import os
import httpx
import pyperclip
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _fetch_email_text(payload: dict) -> str:
    """Read full email body from API (response may be chunked; UI updates once at end)."""
    url = f"{API_BASE}/generate-email"
    parts: list[str] = []
    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", url, json=payload) as response:
            if response.status_code != 200:
                detail = response.text[:2000] if response.text else response.reason_phrase
                raise RuntimeError(f"{response.status_code}: {detail}")
            for chunk in response.iter_raw():
                if chunk:
                    parts.append(chunk.decode("utf-8", errors="replace"))
    return "".join(parts)


def _page_css():
    st.markdown(
        """
        <style>
        :root {
            --tan: #C2B280;
            --coral: #E35336;
            --sage: #98A869;
            --navy: #272757;
        }
        .stApp {
            background: #FFFFFF;
        }
        [data-testid="stHeader"] {
            background-color: #FFFFFF;
        }
        [data-testid="stAppViewContainer"] > .main {
            background-color: #FFFFFF;
        }
        h1, h2, h3, label, p, span, .stMarkdown { color: var(--navy) !important; }
        .stCaption { color: var(--sage) !important; }
        hr {
            border-color: rgba(194, 178, 128, 0.45) !important;
        }
        /* Corners: use box-shadow “ring” instead of border so curves stay continuous (no clipped corners). */
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
            border-radius: 0.5rem !important;
            border: none !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 1px rgba(152, 168, 105, 0.55) !important;
        }
        div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
            box-shadow: 0 0 0 2px rgba(39, 39, 87, 0.35) !important;
        }
        div[data-testid="stTextInput"] input {
            color: var(--navy) !important;
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            border-radius: 0.5rem !important;
        }
        div[data-testid="stTextArea"] div[data-baseweb="textarea"] {
            border-radius: 0.5rem !important;
            border: none !important;
            background-color: #FFFFFF !important;
            box-shadow: 0 0 0 1px rgba(152, 168, 105, 0.55) !important;
        }
        div[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
            box-shadow: 0 0 0 2px rgba(39, 39, 87, 0.35) !important;
        }
        div[data-testid="stTextArea"] textarea {
            color: var(--navy) !important;
            background: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            border-radius: 0.5rem !important;
        }
        .stTextInput input, .stTextArea textarea {
            color: var(--navy) !important;
        }
        div[data-testid="stTextInput"]:not(:has([data-baseweb="input"])) input {
            border-radius: 0.5rem !important;
            border: none !important;
            box-shadow: 0 0 0 1px rgba(152, 168, 105, 0.55) !important;
            background-color: #FFFFFF !important;
        }
        div[data-testid="stTextInput"]:not(:has([data-baseweb="input"])) input:focus {
            box-shadow: 0 0 0 2px rgba(39, 39, 87, 0.35) !important;
            outline: none !important;
        }
        div[data-testid="stTextArea"]:not(:has([data-baseweb="textarea"])) textarea {
            border-radius: 0.5rem !important;
            border: none !important;
            box-shadow: 0 0 0 1px rgba(152, 168, 105, 0.55) !important;
            background-color: #FFFFFF !important;
        }
        div[data-testid="stTextArea"]:not(:has([data-baseweb="textarea"])) textarea:focus {
            box-shadow: 0 0 0 2px rgba(39, 39, 87, 0.35) !important;
            outline: none !important;
        }
        .stButton > button,
        .stButton > button * {
            color: #FFFFFF !important;
        }
        .stButton > button {
            background-color: var(--navy) !important;
            border: 1px solid var(--navy) !important;
        }
        .stButton > button:hover {
            background-color: var(--coral) !important;
            border-color: var(--coral) !important;
        }
        div[class*="st-key-vd_generate_email"] .stButton > button {
            background-color: var(--coral) !important;
            border-color: var(--coral) !important;
        }
        div[class*="st-key-vd_generate_email"] .stButton > button:hover {
            filter: brightness(0.94);
        }
        div[data-testid="stExpander"] {
            background-color: rgba(194, 178, 128, 0.12);
            border: none !important;
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 0 0 1px rgba(194, 178, 128, 0.85);
            transform: translateZ(0);
            -webkit-font-smoothing: antialiased;
        }
        div[data-testid="stExpander"] details {
            border: none !important;
            border-radius: inherit;
        }
        div[data-testid="stExpander"] summary {
            color: var(--navy) !important;
            border: none !important;
            border-radius: 0.75rem 0.75rem 0 0;
            list-style: none;
        }
        div[data-testid="stExpander"] details:not([open]) > summary {
            border-radius: 0.75rem !important;
        }
        div[data-testid="stExpander"] summary::-webkit-details-marker {
            display: none;
        }
        /* Inner Streamlit blocks: avoid extra square outlines that fight the card radius */
        div[data-testid="stExpander"] [data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stStatus"] {
            border-left: 3px solid var(--sage);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_page_css()

st.title("Vendor outreach")
st.caption("Generate a draft, edit it, then refine with instructions.")

st.session_state.setdefault("email_draft", "")

with st.expander("Vendor details", expanded=True):
    vendor = st.text_input("Vendor name", placeholder="Acme Corp")
    product = st.text_input("Product / service", placeholder="Enterprise license renewal")
    deadline = st.text_input("Deadline", placeholder="March 15, 2026")
    initial_instruction = st.text_input(
        "Optional tone / style (first draft only)",
        placeholder='e.g. "formal", "very brief"',
        key="initial_instruction",
    )

gen_clicked = st.button("Generate email", type="primary", key="vd_generate_email")

st.divider()

ref_col, regen_col = st.columns([4, 1])
with ref_col:
    refine_instr = st.text_input(
        "Refinement instruction",
        placeholder='e.g. "shorter", "more casual", "add urgency"',
        key="refine_instr",
    )
with regen_col:
    st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    regen_clicked = st.button("Regenerate", key="vd_regenerate")

gen_ok = False
if gen_clicked:
    if not (vendor and product and deadline):
        st.error("Fill vendor name, product/service, and deadline before generating.")
    else:
        instr = (initial_instruction or "").strip() or None
        payload = {
            "vendor_name": vendor,
            "product_or_service": product,
            "deadline": deadline,
            "instruction": instr,
            "previous_email": None,
        }
        try:
            with st.spinner("Generating…"):
                st.session_state.email_draft = _fetch_email_text(payload)
            gen_ok = True
        except Exception as e:
            st.error(f"Generation failed: {e}")

regen_handled = False
if regen_clicked:
    draft = (st.session_state.get("email_draft") or "").strip()
    if not (vendor and product and deadline):
        st.error("Vendor details are required for regeneration.")
    elif not draft:
        st.error("Nothing to refine — generate or paste an email first.")
    elif not (refine_instr or "").strip():
        st.error("Add a refinement instruction (e.g. shorter, casual).")
    else:
        regen_handled = True
        payload = {
            "vendor_name": vendor,
            "product_or_service": product,
            "deadline": deadline,
            "instruction": refine_instr.strip(),
            "previous_email": draft,
        }
        try:
            with st.spinner("Refining…"):
                st.session_state.email_draft = _fetch_email_text(payload)
        except Exception as e:
            st.error(f"Regeneration failed: {e}")
            regen_handled = False

st.text_area(
    "Email (editable)",
    height=320,
    key="email_draft",
    label_visibility="visible",
)

if gen_ok:
    st.success("Draft ready.")
if regen_handled:
    st.success("Regenerated.")

if st.button("Copy to clipboard", key="vd_copy"):
    try:
        pyperclip.copy(st.session_state.get("email_draft") or "")
        st.success("Copied.")
    except Exception as e:
        st.warning(f"Copy failed ({e}). Select the text manually.")
