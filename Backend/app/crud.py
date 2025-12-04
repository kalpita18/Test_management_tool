from sqlalchemy import select
from models import TestCase, TestExecution, TestSuite, Project
from collections import Counter

def get_cases_with_latest_status(db, suite_id: int):
    """
    Return list of cases in suite with latest_status and latest_comment (if any).
    """
    cases = db.query(TestCase).filter(TestCase.suite_id == suite_id).order_by(TestCase.id).all()
    results = []
    for c in cases:
        latest = db.query(TestExecution).filter(TestExecution.test_case_id == c.id).order_by(TestExecution.executed_at.desc()).first() #this is a select query with where clause and order by condition
        results.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "priority": c.priority,
            "steps": c.steps,
            "latest_status": latest.status if latest else None,
            "latest_comment": latest.comment if latest else None,
            "latest_executed_at": latest.executed_at.isoformat() if latest and latest.executed_at else None
        })
    return results

def get_case_detail_with_executions(db, case_id: int):
    c = db.query(TestCase).get(case_id)
    if not c:
        return None
    executions = db.query(TestExecution).filter(TestExecution.test_case_id == case_id).order_by(TestExecution.executed_at.desc()).all()
    exec_list = [
        {"id": e.id, "status": e.status, "comment": e.comment, "executed_at": e.executed_at.isoformat() if e.executed_at else None}
        for e in executions
    ]
    return {
        "case_r": {"id": c.id, "title": c.title, "description": c.description, "priority": c.priority, "steps": c.steps},
        "executions": exec_list
    }

#not used now
def get_next_case_in_suite(db, suite_id: int, after_case_id: int | None):
    q = db.query(TestCase).filter(TestCase.suite_id == suite_id)
    if after_case_id:
        q = q.filter(TestCase.id > after_case_id)
    q = q.order_by(TestCase.id)
    return q.first()

def insert_execution(db, case_id: int, status: str, comment:str| None):
    te = TestExecution(test_case_id=case_id, status=status, comment=comment)
    db.add(te)
    db.commit()
    db.refresh(te)
    return te

def compute_suite_summary_using_latest(db, suite_id: int):
    rows = get_cases_with_latest_status(db, suite_id)
    total = len(rows)
    normalized = [
    r["latest_status"] if r["latest_status"] not in (None, "", "null")
    else "NOT STARTED"
    for r in rows]
    status_counts = Counter(normalized)
    failed = [r for r in rows if r["latest_status"] == "FAIL"]
    blocked = [r for r in rows if r["latest_status"]=="BLOCKER"]
    return status_counts#,{"failed_count": len(failed),
        #"failed": failed, "blocked": blocked}
        #"total_cases": total,
        #"passed": passed,

def delete_all_test_cases_from_suite(db, suite_id:int):
    subq = db.query(TestCase.id).filter(TestCase.suite_id == suite_id).subquery()
    #delete execution
    db.query(TestExecution).filter(TestExecution.test_case_id.in_(subq)).delete(synchronize_session=False)
    db.commit()

    #delete test cases
    cases = db.query(TestCase).filter(TestCase.suite_id == suite_id).delete(synchronize_session=False)
    db.commit()
    if cases==0:
        return "No cases present to delete"
    return f"{cases} test case(s) deleted"
    
def get_all_suites_details(db):
    #joining 2 tables to get the data of project name
    '''suites = db.query(TestSuite.id, 
                    TestSuite.name,
                    Project.name).join(Project, TestSuite.project_id==Project.id)
                    .order_by(TestSuite.id).all()'''
    #list_s = [{"id": s[0], "suite_name": s[1], "project_name": s[2]}
    #          for s in suites]
    #return list_s
        
    suites = (db.query(TestSuite.id.label("id"), 
                    TestSuite.name.label("suite_name"),
                    Project.name.label("project_name")).join(Project, TestSuite.project_id==Project.id)\
                    .order_by(TestSuite.id).all())
    # Convert each row to a dict cleanly
    return [dict(row._mapping) for row in suites]

def delete_suite_crud(db, suite_id:int):
    #count_ts = db.query(TestCase).filter(TestCase.suite_id ==suite_id).all
    #if len(count_ts)!=0:
    #    return "Kindly delete the test cases first linked to this suite before suite"
    #else:
    del_s = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    db.delete(del_s)
    db.commit()
    message = f"Test Suite got deleted"
    return message