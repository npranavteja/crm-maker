from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Sponsor(Base):
    __tablename__ = "sponsors"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String)
    contact = Column(String)
    role = Column(String)
    email = Column(String)
    phone = Column(String)
    linkedin = Column(String)
    amount = Column(Integer, default=0)
    priority = Column(String, default="medium")
    stage = Column(String, default="prospecting")
    category = Column(String)
    tags = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    sponsor_id = Column(Integer)
    action = Column(String)
    note = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Template(Base):
    __tablename__ = "templates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    subject = Column(String)
    body = Column(String)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    sponsor_id = Column(Integer)
    title = Column(String)
    due_date = Column(String)
    priority = Column(String, default="medium")
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    sponsor_id = Column(Integer)
    body = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
