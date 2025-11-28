from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func, Text
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    suites = relationship("TestSuite", back_populates="project", cascade="all, delete-orphan") #If a TestSuite no longer belongs to any Project → delete it automatically.

class TestSuite(Base):
    __tablename__ = "test_suites"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    project = relationship("Project", back_populates="suites")
    cases = relationship("TestCase", back_populates="suite", cascade="all, delete-orphan")

class TestCase(Base):
    __tablename__ = "test_cases"
    id = Column(Integer, primary_key=True, index=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String, nullable=True)
    steps = Column(String, nullable=True, default=[])  # list of dicts
    suite = relationship("TestSuite", back_populates="cases")
'''
class TestRun(Base):
    __tablename__ = "test_runs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    suite_id = Column(Integer, ForeignKey("test_suites.id"), nullable=True)
    environment = Column(String, nullable=True)
    executed_by = Column(String, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

class TestRunCase(Base):
    __tablename__ = "test_run_cases"
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    status = Column(String, nullable=False)  # PASSED / FAILED / SKIPPED
    comment = Column(Text, nullable=True)
    executed_at = Column(DateTime, server_default=func.now())
    '''
class TestExecution(Base):
    """
    Flat history of every execution of a test case.
    Each execution row records the status and optional comment and timestamp.
    """
    __tablename__ = "test_executions"
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    status = Column(String, nullable=False)   # PASSED / FAILED / SKIPPED
    comment = Column(Text, nullable=True)
    executed_at = Column(DateTime, server_default=func.now())