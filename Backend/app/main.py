from fastapi import FastAPI, UploadFile, File, HTTPException, Query
import httpx
from .utils import parse_testcase_excel
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from .db import *
from .models import *
from .crud import *
from fastapi.responses import JSONResponse
from typing import Dict


@asynccontextmanager
async def lifespan(app:FastAPI): #this code will get execute once server has started, basically on the startup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        default_project = db.query(Project).filter(Project.name == "SAMS").first()
        if not default_project:
            p = Project(name="SAMS")
            db.add(p)
            db.commit()
            db.refresh(p)
            default_suite = TestSuite(project_id=p.id, name="Default Suite")
            db.add(default_suite)
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/api/testcases/upload")
async def upload_testcases(file: UploadFile = File(...)): #this means file is required and file must be included in the request body
    if not file.filename.endswith((".xlsx",".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files supported")
    content = await file.read() #Reads the entire excel into memory, content is now b"...excel bytes...
    try:
        parsed = parse_testcase_excel(content) #here excel gets parsed
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel: {e}")
    
    created = [] #create an empty list
    db = SessionLocal() #create a new db session
    try:
        first_row_keys = set(parsed[0].keys())
        print(first_row_keys)
        if "title" in first_row_keys:
            default_suite = db.query(TestSuite).filter(TestSuite.name == "Default Suite").first()
            for p in parsed:
                suitename = p.get("suite") or "Default"
                if suitename!="Default":
                    s = db.query(TestSuite).filter(TestSuite.name==suitename).first()
                    if not s:
                        s = TestSuite(project_id=default_suite.project_id, name=suitename)
                        db.add(s)
                        db.commit()
                        db.refresh(s)
                    target_suite = s
                else:
                    target_suite = default_suite
                
                tc = TestCase(
                    suite_id=target_suite.id,
                    title=p["title"],
                    description=p.get("description") or "",
                    priority=p.get("priority") or "",
                    steps=p.get("steps") or "",
                )
                db.add(tc)
                db.commit()
                db.refresh(tc)
                created.append({"id": tc.id, "title": tc.title, "suite": target_suite.name, "steps": tc.steps})
        else:
            return JSONResponse(
        status_code=400,
        content="Excel is not proper")
            
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

    return {"Test cases got uploaded successfully"}

@app.get("/api/suites/{suite_id}/cases")
def list_cases_for_suite(suite_id):
    db = SessionLocal()
    try:
        cases = get_cases_with_latest_status(db, suite_id)
        return {"cases": cases}
    finally:
        db.close()

@app.get("/api/cases/{case_id}")
def case_detail(case_id):
    db = SessionLocal()
    try:
        detail = get_case_detail_with_executions(db, case_id)
        if not detail:
            return JSONResponse (status_code=404,
            content="Test case not found")
        return detail
    finally:
        db.close()

@app.post("/api/execute/{case_id}")
def execute_case(case_id, status: str, comment: str|None = None, retry: bool = False, suite_id: int|None = None):
    status = status.upper()
    if status not in ("PASS", "FAIL", "BLOCKER", "IN PROGRESS"):
        return {"Invalid Status"}
    db = SessionLocal()
    try:
        insert_execution(db, case_id, status, comment)
        if retry:
            tc = db.query(TestCase).get(case_id)
            if not tc:
                raise JSONResponse(status_code=404, content="Test case not found")
            return {"next": {"id": tc.id, "title": tc.title, "description": tc.description, "steps": tc.steps}}
        if suite_id:
            #not using this feature as of now 
            tc = get_next_case_in_suite(db, suite_id, after_case_id=case_id)
            if not tc:
                return {"next": None}
            return {"next": {"id": tc.id, "title": tc.title, "description": tc.description, "steps": tc.steps}}
        return {"next": None}
    finally:
        db.close()

@app.get("/api/suites/{suite_id}/summary")
def suite_summary(suite_id: int):
    db = SessionLocal()
    try:
        summary = compute_suite_summary_using_latest(db, suite_id)
        return summary
    finally:
        db.close()

@app.delete("/api/suites/{suite_id}/cases")
def delete_testcases(suite_id:int):
    db = SessionLocal()
    try:
        delete_tc = delete_all_test_cases_from_suite(db,suite_id)
        return delete_tc
    finally:
        db.close()

@app.get("/api/suites")
def get_all_suites():
    db = SessionLocal()
    try:
        data_suites = get_all_suites_details(db)
        return data_suites
    finally:
        db.close()

@app.delete("/api/suites/{suite_id}")
def delete_suite(suite_id:int):
    db = SessionLocal()
    try:
        del_suite = delete_suite_crud(db, suite_id)
        return del_suite
    finally:
        db.close()

@app.post("/api/testcases/single/")
def add_single_tc(item: Dict):
    db = SessionLocal()
    try:
        tc = TestCase(
                        suite_id=item["suite_id_tc"],
                        title=item["title_tc"],
                        description=item.get("description") or "",
                        priority=item.get("priority_tc") or "",
                        steps=item.get("steps_tc") or "",
                    )
        db.add(tc)
        db.commit()
        db.refresh(tc)
        return "Test case got added successfully"
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/projects")
def get_projects():
    db = SessionLocal()
    try:
        data_proj = db.query(Project).order_by(Project.id).all()
        return data_proj
    finally:
        db.close()

@app.post("/api/add/suite")
def add_suite(item_suite: Dict):
    db = SessionLocal()
    try:
        ts = TestSuite(
                        project_id = item_suite["projectid"],
                        name=item_suite["suitename"],
                    )
        db.add(ts)
        db.commit()
        db.refresh(ts)
        return "Test Suite got added successfully"
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()