import streamlit as st
import httpx
import asyncio
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
import matplotlib.pyplot as plt
from datetime import datetime

API_BASE = "http://localhost:8000/api"
st.set_page_config(page_title="Test Case Management", layout="wide")
#st.title("Test Case Management")

tab = st.sidebar.radio("select",("Test Suites","Test Cases & Summary", "Upload Test cases"))

#we have cached this suites table to avoid fetching everytime from db
@st.cache_data
def fetch_suites():
    suites_data = httpx.get(f"{API_BASE}/suites", timeout=10)
    if suites_data.status_code==200:
        return suites_data.json()
    else:
        st.error(suites_data.text)

if tab == "Test Suites":
    st.header("Test Suites")

    if st.button("Refresh to fetch new suites"):
        st.cache_data.clear()
    
    try:
        data = fetch_suites()
        st.dataframe(data)
    except Exception as e:
        st.error(str(e))


if tab == "Test Cases & Summary":
    # --- suite selection ---
    suite_id_col, refresh_button, delete_tcs = st.columns(3)

    #for fetching test cases and summary
    get_tcs, get_summ = st.columns(2)
    suite_idd = suite_id_col.number_input("Suite id", value=1, min_value=1, step=1)
    
    #delete test cases
    if delete_tcs.button("Delete test cases"):
        delete_case = httpx.delete(f"{API_BASE}/suites/{suite_idd}/cases")
        if delete_case.status_code!=200:
            st.error(delete_case.text)
        else:
            st.success(delete_case.text)

    if refresh_button.button("Refresh cases"):
        st.rerun()
        #load test cases for that particular suite it
    try:
        resp = httpx.get(f"{API_BASE}/suites/{suite_idd}/cases", timeout=10)
    except Exception as e:
        st.error(f"Could not reach backend: {e}")
        st.stop()

    if resp.status_code!=200:
        st.error(f"Failed to load cases: {resp.text}")
        st.stop()

    #test cases are fetched here
    case = resp.json().get("cases",[])

    #show case summary if cases found and info if not found
    if not case:
        st.info("No test cases found in this suite. Upload or create testcases first.")
    else:
        # show all the test cases of that suite
        # ---------- CHANGE: use session_state to persist the table across reruns ----------
        if "show_cases" not in st.session_state:
            st.session_state["show_cases"] = False

        if get_tcs.button("Get Test Cases"):

            st.markdown("-----------")
            st.session_state["show_cases"] = True
            st.session_state["show_summary"] = False

        # Only render the table when show_cases is True
        if st.session_state["show_cases"] == True:
            # display cases table (AgGrid version)
            st.subheader("Test cases status")

            df_rows = []
            for c in case:
                df_rows.append({
                    "id": c["id"],
                    "title": c["title"],
                    "priority": c.get("priority") or "",
                    "latest_status": c.get("latest_status") or "NOT STARTED",
                    "last_executed_at": c.get("latest_executed_at") or ""
                })
            df = pd.DataFrame(df_rows)

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_selection(selection_mode="single", use_checkbox=False)
            gb.configure_default_column(sortable=True, filter=True, resizable=True)
            grid_options = gb.build()

            st.write("Click a row to select and load details.")
            grid_response = AgGrid(
                df,
                gridOptions=grid_options,
                enable_enterprise_modules=False,
                fit_columns_on_grid_load=True,
                height=400,
                reload_data=True,
                allow_unsafe_jscode=True,
                update_mode=GridUpdateMode.SELECTION_CHANGED,   # <-- important
                data_return_mode=DataReturnMode.FILTERED_AND_SORTED  # ensures returned rows match view
            )

            # Get selected rows (will be [] if none selected)
            selected_raw = grid_response.get("selected_rows")
            if selected_raw is None:
                selected = []
            elif isinstance(selected_raw, list):
                # already a list of dicts
                selected = selected_raw
            elif isinstance(selected_raw, pd.DataFrame):
                # convert DataFrame to list of dicts
                selected = selected_raw.to_dict(orient="records")
            else:
                # fallback: try to coerce to list safely
                try:
                    selected = list(selected_raw)
                except Exception:
                    selected = []
            
            #st.write("DEBUG: selected rows count:", len(selected))
            if selected:
                preview = selected[0]
                id_select_resp = httpx.get(f"{API_BASE}/cases/{preview['id']}", timeout=10)
                if id_select_resp.status_code!=200:
                    st.error(f"Failed to load test case: {id_select_resp.text}")
                else:
                    payload = id_select_resp.json()
                    case_d = payload["case_r"]
                    execution = payload["executions"]

                    #displays test case data
                    st.markdown(f"### Test Case: {case_d['id']} - {case_d['title']}  ")
                    if case_d.get("description"):
                        st.write(f"**Description:** {case_d["description"]}")
                    if case_d.get("priority"):
                        st.write(f"**Priority:** {case_d['priority']}")
                    st.write("**Steps:**")
                    st.write(case_d.get("steps") or [])


                    #Display Execution
                    st.markdown("#### Execution history (latest first)")
                    if execution:
                        for ex in execution:
                            st.write(f"- {ex['executed_at']} — **{ex['status']}** — {ex.get('comment','')}")
                    else:
                        st.write("_No executions yet_")

                    #comment section
                    st.markdown("--------")
                    comment = st.text_area("Comment(optional)")

                    col1, col2, col3, col4 = st.columns(4)
                    if col1.button("PASS ✅"): #text on buttom
                        resp = httpx.post(f"{API_BASE}/execute/{case_d['id']}", params={"status": "PASS", "retry": False, "comment": comment})
                        if resp.status_code!=200:
                            st.error(resp.text)
                        else:
                            st.success("Recorded PASSED")
                            st.rerun()
                    if col2.button("FAIL 🟫"):
                        resp = httpx.post(f"{API_BASE}/execute/{case_d['id']}", params={"status": "FAIL", "retry": False, "comment": comment})
                        if resp.status_code!=200:
                            st.error(resp.text)
                        else:
                            st.success("Recorded FAILED")
                            st.rerun()
                    if col3.button("BLOCKER 🔴"):
                        resp = httpx.post(f"{API_BASE}/execute/{case_d['id']}", params={"status": "BLOCKER", "retry": False, "comment": comment})
                        if resp.status_code!=200:
                            st.error(resp.text)
                        else:
                            st.success("Recorded BLOCKER")
                            st.rerun()
                    if col4.button("IN PROGRESS 🔵"):
                        resp = httpx.post(f"{API_BASE}/execute/{case_d['id']}", params={"status": "IN PROGRESS", "retry": False, "comment": comment})
                        if resp.status_code!=200:
                            st.error(resp.text)
                        else:
                            st.success("Recorded In Progress")
                            st.rerun()

        if "show_summary" not in st.session_state:
            st.session_state["show_summary"] = False

        if get_summ.button("Get Summary"):
            st.markdown("-----------")
            st.session_state["show_summary"] = True
            st.session_state["show_case"] = False

        if st.session_state["show_summary"] == True:
            st.subheader("Test summary  status")

            resp_summ = httpx.get(f"{API_BASE}/suites/{suite_idd}/summary")
            if resp_summ.status_code!=200:
                st.error(resp_summ.text)
            else:
                data = resp_summ.json()
                data_status = pd.DataFrame({'Status':list(data.keys()), 'Count': list(data.values())})
                #create a chart
                #st.bar_chart(data_status.set_index('Status'))
                fig, ax = plt.subplots(figsize=(4,4))

                total = data_status["Count"].sum()

                def fmt(pct):
                    count = int(round(pct * total / 100))
                    return f"{count}\n({pct:.1f}%)"
                
                ax.pie(data_status["Count"], labels=data_status["Status"],autopct=fmt, startangle=90)
                st.pyplot(fig)


if tab == "Upload Test cases":
    uploaded = st.file_uploader("Upload a file",type=["xlsx", "xls"])
    if uploaded:
        mime = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if uploaded.name.endswith(".xlsx")
        else "application/vnd.ms-excel")
        files = {"file": (uploaded.name, uploaded.getvalue(), mime)}
        resp = httpx.post(f"{API_BASE}/testcases/upload", files=files)
        if resp.status_code == 200:
            st.success("Test cases got uploaded successfully")
            #st.json(resp.json())
        else:
            st.error(f"Upload failed: {resp.text}")

