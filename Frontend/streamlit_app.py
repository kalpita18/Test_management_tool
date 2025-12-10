import streamlit as st
import httpx
import asyncio
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
import matplotlib.pyplot as plt
from datetime import datetime
import os

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

API_BASE = BACKEND_URL
st.set_page_config(page_title="Test Case Management", layout="wide")
#st.title("Test Case Management")

tab = st.sidebar.radio("Select",("🧪 Test Suites","📋 Test Cases & Summary", "📤 Upload Test cases"),  label_visibility="collapsed")

#we have cached this suites table to avoid fetching everytime from db
@st.cache_data
def fetch_suites():
    suites_data = httpx.get(f"{API_BASE}/api/suites", timeout=10)
    if suites_data.status_code==200:
        return suites_data.json()
    else:
        st.error(suites_data.text)


def fetch_projects():
    projects_data = httpx.get(f"{API_BASE}/api/projects", timeout=10)
    return projects_data.json()

if tab == "🧪 Test Suites":
    st.header("🧪 Test Suites")
    if st.button("🔄 Refresh Suites"):
        st.cache_data.clear()
    
    try:
        data = fetch_suites()
        st.dataframe(data)
    except Exception as e:
        st.error(str(e))
    
    st.markdown("-----")
    st.markdown("#### Add Test Suite")
    data_proj = fetch_projects()
    with st.form("suite_form", clear_on_submit=True):
        name = st.text_input("Enter Suite Name")
        select_project = st.selectbox("Choose Project", data_proj, format_func=lambda x: x['name'])
        project_id = select_project['id']
        submitted = st.form_submit_button("Add Suite")
        if submitted:
            if name!='':
                payload = {"projectid":project_id, "suitename": name}
                resp_suite = httpx.post(f"{API_BASE}/api/add/suite", json=payload)
                if resp_suite.status_code!=200:
                    st.error(resp_suite.text)
                else:
                    st.success(resp_suite.text)
                    st.cache_data.clear()
                    st.rerun()
            if name=="":
                st.error("Please enter the name")



if tab == "📋 Test Cases & Summary":
    # --- suite selection ---
    suite_col, refresh_button, delete_tcs, delete_suite = st.columns([1.5,0.8,1,1])

    st.markdown("-----------")

    #for fetching test cases and summary
    get_tcs, get_summ = st.columns(2)
    data_s = fetch_suites()
    #format used in Streamlit’s selectbox to control what text is displayed for each item in the dropdown.
    select_name = suite_col.selectbox("Choose suite name", data_s, format_func=lambda x:x["suite_name"])
    suite_idd = select_name["id"]
    #suite_idd = suite_id_col.number_input("Enter Suite id to fetch cases", value=1, min_value=1, step=1)

    if "show_cases" not in st.session_state:
            st.session_state["show_cases"] = False
    if "show_summary" not in st.session_state:
            st.session_state["show_summary"] = False
    if "cases_data" not in st.session_state:
        st.session_state["cases_data"] = [] 
    if "data_loaded_for_suite" not in st.session_state:
        st.session_state["data_loaded_for_suite"] = None  # which suite id was last loaded
    if "refresh_suite" not in st.session_state:
        st.session_state["refresh_suite"] = False
    if "confirm_delete_suite" not in st.session_state:
        st.session_state["confirm_delete_suite"] = False

    #delete test cases
    with delete_tcs:
        st.write("")
        st.write("")
    if delete_tcs.button("🗑️ Delete test cases"):
        delete_case = httpx.delete(f"{API_BASE}/api/suites/{suite_idd}/cases")
        if delete_case.status_code!=200:
            st.error(delete_case.text)
        else:
            st.success(delete_case.text)
            st.session_state['cases_data'] = []
    
    #delete suite
    with delete_suite:
        st.write("")
        st.write("")
    # when user first clicks this, set a flag (no immediate confirmation buttons expectation)
    if delete_suite.button("🗑️ Delete test suite"):
        st.session_state["confirm_delete_suite"] = True
        st.session_state["data_loaded_for_suite"] = None
        st.session_state["refresh_suite"] = False

    # render confirmation UI whenever flag is True
    if st.session_state["confirm_delete_suite"] == True:
        st.warning("This will delete the linked test cases as well. Are you sure?")
        yes, no = st.columns(2)
        if yes.button("Yes", key="confirm_delete_yes"):
            resp_suite = httpx.delete(f"{API_BASE}/api/suites/{suite_idd}")
            if resp_suite.status_code==200:
                st.success(resp_suite.text)
                st.session_state["confirm_delete_suite"] = False
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(resp_suite.text)
                st.session_state["confirm_delete_suite"] = False
        
        if no.button("No", key="confirm_delete_no"):
            st.info("Delete cancelled.")
            st.session_state["confirm_delete_suite"] = False

    with refresh_button:
        st.write("")
        st.write("")
    if refresh_button.button("🔄 Fetch data", key="btn_fetch_data"):
        st.session_state["refresh_suite"] = True
        st.session_state["confirm_delete_suite"] = False
        st.session_state["show_cases"] = False
        st.session_state["show_summary"] = False
        st.rerun()

    #load test cases for that particular suite it
    if st.session_state["refresh_suite"] == True:
        try:
            resp = httpx.get(f"{API_BASE}/api/suites/{suite_idd}/cases", timeout=10)
        except Exception as e:
            st.error(f"Could not reach backend: {e}")
            st.stop()

        if resp.status_code!=200:
            st.error(f"Failed to load cases: {resp.text}")
            st.stop()

        #test cases are fetched here
        st.session_state["cases_data"] = resp.json().get("cases",[])
        st.session_state["data_loaded_for_suite"] = suite_idd


        #show case summary if cases found and info if not found
        if len(st.session_state['cases_data'])==0:
            st.info("No test cases found in this suite. Upload or create testcases first.")
        if st.session_state["data_loaded_for_suite"] == suite_idd and st.session_state["cases_data"]:
            # show all the test cases of that suite
            # ---------- CHANGE: use session_state to persist the table across reruns ----------
            if get_tcs.button("📋 Get Test Cases"):

                st.markdown("-----------")
                st.session_state["show_cases"] = True
                st.session_state["show_summary"] = False

            # Only render the table when show_cases is True
            if st.session_state["show_cases"] == True:
                case = st.session_state["cases_data"]
                # display cases table (AgGrid version)
                st.subheader("📄 Test cases status")

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
                    id_select_resp = httpx.get(f"{API_BASE}/api/cases/{preview['id']}", timeout=10)
                    if id_select_resp.status_code!=200:
                        st.error(f"Failed to load test case: {id_select_resp.text}")
                    else:
                        payload = id_select_resp.json()
                        case_d = payload["case_r"]
                        execution = payload["executions"]

                        #displays test case data
                        st.markdown(f"### Test Case: {case_d['id']} - {case_d['title']}  ")
                        if case_d.get("description"):
                            st.write(f"**Description:** {case_d['description']}")
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
                            resp = httpx.post(f"{API_BASE}/api/execute/{case_d['id']}", params={"status": "PASS", "retry": False, "comment": comment})
                            if resp.status_code!=200:
                                st.error(resp.text)
                            else:
                                st.success("Recorded PASSED")
                                st.rerun()
                        if col2.button("FAIL 🟫"):
                            resp = httpx.post(f"{API_BASE}/api/execute/{case_d['id']}", params={"status": "FAIL", "retry": False, "comment": comment})
                            if resp.status_code!=200:
                                st.error(resp.text)
                            else:
                                st.success("Recorded FAILED")
                                st.rerun()
                        if col3.button("BLOCKER 🔴"):
                            resp = httpx.post(f"{API_BASE}/api/execute/{case_d['id']}", params={"status": "BLOCKER", "retry": False, "comment": comment})
                            if resp.status_code!=200:
                                st.error(resp.text)
                            else:
                                st.success("Recorded BLOCKER")
                                st.rerun()
                        if col4.button("IN PROGRESS 🔵"):
                            resp = httpx.post(f"{API_BASE}/api/execute/{case_d['id']}", params={"status": "IN PROGRESS", "retry": False, "comment": comment})
                            if resp.status_code!=200:
                                st.error(resp.text)
                            else:
                                st.success("Recorded In Progress")
                                st.rerun()

            if get_summ.button("📊 Get Summary"):
                st.session_state["show_summary"] = True
                st.session_state["show_cases"] = False
                st.rerun()

            if st.session_state["show_summary"] == True:
                st.markdown("-----------")
                st.subheader("📈 Test summary  status")

                resp_summ = httpx.get(f"{API_BASE}/api/suites/{suite_idd}/summary")
                if resp_summ.status_code!=200:
                    st.error(resp_summ.text)
                else:
                    data = resp_summ.json()
                    data_status = pd.DataFrame({'Status':list(data.keys()), 'Count': list(data.values())})
                    #create a chart
                    #st.bar_chart(data_status.set_index('Status'))
                    fig, ax = plt.subplots(figsize=(3,3))

                    total = data_status["Count"].sum()

                    def fmt(pct):
                        count = int(round(pct * total / 100))
                        return f"{count}\n({pct:.1f}%)"
                    
                    wedges, texts, autotexts = ax.pie(
                    data_status["Count"],
                    labels=data_status["Status"],
                    autopct=fmt,
                    startangle=90,
                    textprops={"fontsize": 7},
                    wedgeprops=dict(width=0.4),   # <--- donut thickness
                )

                    ax.set(aspect="equal")
                    #ax.pie(data_status["Count"], labels=data_status["Status"],autopct=fmt, startangle=90)
                    #ax.axis('equal')
                    st.pyplot(fig)


if tab == "📤 Upload Test cases":
    st.markdown("#### Upload a file to import test cases")
    uploaded = st.file_uploader("select file",type=["xlsx", "xls"], label_visibility="collapsed")
    if uploaded:
        mime = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if uploaded.name.endswith(".xlsx")
        else "application/vnd.ms-excel")
        files = {"file": (uploaded.name, uploaded.getvalue(), mime)}
        resp = httpx.post(f"{API_BASE}/api/testcases/upload", files=files)
        if resp.status_code == 200:
            st.success("Test cases got uploaded successfully")
            #st.json(resp.json())
        else:
            st.error(f"Upload failed: {resp.text}")

    st.markdown("-----")
    st.markdown("#### Add single test case")
    st.cache_data.clear()
    data_up = fetch_suites()
    with st.form("tc_form", clear_on_submit=True):
        select_name = st.selectbox("Choose suite name", data_up, format_func=lambda x:x["suite_name"])
        suite_id = select_name["id"]
        title = st.text_input("Enter title for test case", key = "title_input")
        steps = st.text_area("Enter steps for test case", key = "steps_input")
        priority = st.selectbox("Choose priority", ["Low", "Medium","High"])
        submitted = st.form_submit_button("Add test case")
        if submitted:
            if title!="":
                payload = {"suite_id_tc":suite_id, "title_tc":title,
                                "steps_tc":steps, "priority_tc":priority}
                resp = httpx.post(f"{API_BASE}/api/testcases/single/", json=payload)
                if resp.status_code!=200:
                    st.error(resp.text)
                else:
                    st.success(resp.text)
            if title=="":
                st.error("Please enter the title")




    