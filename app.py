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
mode = st.radio(
    "Mode",
    ["Demo (show guardrail decision)", "Production (silent block with decoy data)"],
    horizontal=True,
)
with st.form("query_form"):
    user_input = st.text_input(
        "Search employees by name or department",
        value="Alice",
        help="This value is interpolated directly into SQL on purpose.",
    )
    submitted = st.form_submit_button("Send to backend")

if submitted:
    decision = evaluate_input(user_input)
    production_mode = mode.startswith("Production")

    if not production_mode:
        st.write(f"**Guardrail decision:** {'SAFE' if decision.safe else 'BLOCKED'}")
        st.caption(f"Reason: {decision.reason} (source: {decision.source})")
    else:
        st.caption(
            "Production mode hides guardrail reasoning. Blocked requests receive decoy data."
        )

    if decision.safe:
        rows = run_insecure_query(user_input)
        st.success(
            "Showing real data."
            if production_mode
            else f"Input marked SAFE → real database queried at {DB_PATH}."
        )
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
        if production_mode:
            st.info("Showing generic data.")
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