import streamlit as st

from data_backend import DB_PATH, init_db, run_insecure_query
from guardrail import evaluate_input


st.set_page_config(page_title="LLM Guardrail Demo", page_icon="🛡️")

st.title("🛡️ LLM Guardrail Demo")
st.write(
    "A deliberately vulnerable backend (SQLite) sits behind this Streamlit UI. "
    "User input is screened by a lightweight guardrail before hitting the raw SQL query. "
    "If the guardrail thinks the input is malicious, it returns fake data instead of the real database."
)

# Ensure the demo database exists.
init_db()


def fake_rows():
    # Decoy data to return when the guardrail blocks the request.
    return [
        (0, "REDACTED", "redacted@example.com", "Unknown", 0),
        (0, "Honeypot User", "honeypot@example.com", "Unknown", 0),
    ]


st.subheader("Try a query")
with st.form("query_form"):
    user_input = st.text_input(
        "Search employees by name or department",
        value="Alice",
        help="This value is interpolated directly into SQL on purpose.",
    )
    submitted = st.form_submit_button("Send to backend")

if submitted:
    decision = evaluate_input(user_input)
    st.write(f"**Guardrail decision:** {'SAFE' if decision.safe else 'BLOCKED'}")
    st.caption(f"Reason: {decision.reason} (source: {decision.source})")

    if decision.safe:
        rows = run_insecure_query(user_input)
        st.success(f"Input marked SAFE → real database queried at {DB_PATH}.")
        if rows:
            st.dataframe(
                rows,
                column_config={
                    0: st.column_config.TextColumn("id"),
                    1: st.column_config.TextColumn("name"),
                    2: st.column_config.TextColumn("email"),
                    3: st.column_config.TextColumn("department"),
                    4: st.column_config.NumberColumn("salary"),
                },
                hide_index=True,
            )
        else:
            st.info("Query returned no rows.")
    else:
        st.warning("Input blocked → returning fake data instead of hitting the DB.")
        st.dataframe(
            fake_rows(),
            column_config={
                0: st.column_config.TextColumn("id"),
                1: st.column_config.TextColumn("name"),
                2: st.column_config.TextColumn("email"),
                3: st.column_config.TextColumn("department"),
                4: st.column_config.NumberColumn("salary"),
            },
            hide_index=True,
        )

st.divider()
st.subheader("How to use")
st.markdown(
    """
1. Install deps: `pip install -r requirements.txt`
2. Run: `streamlit run app.py`
3. Try benign input like `Alice` (passes) and hostile input like `Alice'; DROP TABLE employees;--` (blocked).
4. Optional: set `GEMINI_API_KEY` to use Gemini instead of regex heuristics.
"""
)
