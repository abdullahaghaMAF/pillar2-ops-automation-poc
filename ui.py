import json
import requests
import streamlit as st

st.set_page_config(page_title="Pillar 2 Ops Assistant (PoC)", layout="wide")

API_BASE = st.sidebar.text_input("API Base URL", value="http://127.0.0.1:8000")
st.sidebar.markdown("---")

st.title("Pillar 2 – Ops Automation Assistant (PoC)")
st.caption("SOP-backed AI guidance • structured intake → Todoist • exception-only escalation • audit logs")

def call_post(path: str, payload: dict, timeout: int = 60):
    url = f"{API_BASE}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    return r

def call_get(path: str, timeout: int = 20):
    url = f"{API_BASE}{path}"
    r = requests.get(url, timeout=timeout)
    return r

colA, colB = st.columns([2, 1])

with colB:
    st.subheader("Quick Actions")
    if st.button("✅ Check API /health"):
        try:
            r = call_get("/health")
            st.write("Status:", r.status_code)
            st.json(r.json())
        except Exception as e:
            st.error("Backend not reachable. Start uvicorn.")
            st.exception(e)

    if st.button("📥 Ingest SOP (/sop/ingest)"):
        try:
            r = call_post("/sop/ingest", {}, timeout=120)
            st.write("Status:", r.status_code)
            st.write("X-Request-Id:", r.headers.get("X-Request-Id"))
            st.json(r.json())
        except Exception as e:
            st.error("SOP ingest failed. Check backend logs.")
            st.exception(e)

with colA:
    tab1, tab2, tab3 = st.tabs(["Ask SOP (AI Assistant)", "Create Task (Intake)", "Demo Mode"])

    # ----------------- Tab 1: Ask SOP -----------------
    with tab1:
        st.subheader("Ask a question (SOP-backed RAG)")
        q = st.text_area(
            "Question",
            value="Which card should I use for company purchases and what invoice details are required?",
            height=90,
        )
        top_k = st.slider("Top-K retrieval", min_value=1, max_value=8, value=4)

        if st.button("Ask", type="primary"):
            try:
                r = call_post("/ask", {"question": q, "top_k": top_k}, timeout=60)
                st.write("Status:", r.status_code)
                st.write("X-Request-Id:", r.headers.get("X-Request-Id"))

                data = r.json()

                left, right = st.columns(2)
                with left:
                    if data.get("needs_escalation"):
                        st.error("⚠️ Escalation required (low SOP confidence / insufficient coverage).")
                    else:
                        st.success("✅ Answered from approved SOPs (no guessing).")

                    st.metric("Confidence", f"{data.get('confidence', 0.0):.2f}")
                    st.subheader("Citations")
                    st.json(data.get("citations", []))

                with right:
                    st.subheader("Assistant Output")
                    if "result" in data:
                        try:
                            st.json(json.loads(data["result"]))
                        except Exception:
                            st.code(data["result"])
                    else:
                        st.write(data.get("answer", ""))

            except Exception as e:
                st.error("Backend not reachable. Start uvicorn and ensure API Base URL is correct.")
                st.exception(e)

    # ----------------- Tab 2: Create Task -----------------
    with tab2:
        st.subheader("Intake → Routing → Todoist task + enrichment comment")

        msg = st.text_area(
            "Incoming request (simulating WhatsApp/Email)",
            value="Please buy a laptop for the intern using Amazon. Ensure invoice is correct and upload it to the invoices folder.",
            height=90,
        )
        channel = st.selectbox("Channel", ["whatsapp_mock", "email_mock", "sheet_mock"], index=0)

        if st.button("Create Todoist Task", type="primary"):
            try:
                r = call_post("/intake", {"channel": channel, "message": msg}, timeout=60)
                st.write("Status:", r.status_code)
                st.write("X-Request-Id:", r.headers.get("X-Request-Id"))

                data = r.json()
                if data.get("ok"):
                    st.success("✅ Task created successfully in Todoist.")
                    st.write("Todoist Task ID:", data.get("task_id"))
                    st.write("Todoist Comment ID:", data.get("comment_id"))
                    st.subheader("Parsed Payload")
                    st.json(data.get("payload", {}))
                else:
                    st.error("Task creation did not return ok=true")
                    st.json(data)

            except Exception as e:
                st.error("Backend not reachable. Start uvicorn and ensure API Base URL is correct.")
                st.exception(e)

    # ----------------- Tab 3: Demo Mode -----------------
    with tab3:
        st.subheader("One-click demo (recommended for trial walkthrough)")
        st.caption("Runs the exact sequence: Ingest SOP → Ask SOP question → Create Todoist task.")

        demo_q = "What billing address and TRN should be used for invoices?"
        demo_intake = "Please buy a laptop for the intern using Amazon. Ensure invoice is correct and upload it to the invoices folder."

        if st.button("▶ Run Demo Sequence", type="primary"):
            try:
                st.write("1) Ingest SOP...")
                r1 = call_post("/sop/ingest", {}, timeout=120)
                st.write("SOP ingest status:", r1.status_code)

                st.write("2) Ask SOP question...")
                r2 = call_post("/ask", {"question": demo_q, "top_k": 4}, timeout=60)
                data2 = r2.json()
                st.write("Ask status:", r2.status_code)
                if data2.get("needs_escalation"):
                    st.warning("Ask resulted in escalation (still acceptable; threshold is conservative).")
                st.metric("Confidence", f"{data2.get('confidence', 0.0):.2f}")
                st.json(data2.get("citations", []))

                st.write("3) Create Todoist task from intake...")
                r3 = call_post("/intake", {"channel": "whatsapp_mock", "message": demo_intake}, timeout=60)
                data3 = r3.json()
                st.write("Intake status:", r3.status_code)
                if data3.get("ok"):
                    st.success("✅ Demo completed: Task created in Todoist with enrichment comment.")
                    st.write("Task ID:", data3.get("task_id"))
                    st.write("Comment ID:", data3.get("comment_id"))
                else:
                    st.error("Demo intake failed")
                    st.json(data3)

            except Exception as e:
                st.error("Backend not reachable. Start uvicorn and ensure API Base URL is correct.")
                st.exception(e)
