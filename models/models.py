from sqlalchemy import Column, Integer, String, Float, DateTime, LargeBinary, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from urllib.parse import quote_plus

Base = declarative_base()


class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    client_mgr = Column(String)
    client_email = Column(String)
    client_addr = Column(String)
    client_phone = Column(String)
    payment_freq = Column(String)
    client_type = Column(String)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, index=True)
    txn_date = Column(DateTime)
    candidate_id = Column(Integer, ForeignKey('candidates.id'))
    client_id = Column(Integer, ForeignKey('clients.id'))
    recruiter_id = Column(Integer)
    referral_id = Column(Integer)
    client_price = Column(Float)
    referral_price = Column(Float)
    recruiter_price = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    num_payments_received = Column(Integer)
    total_client_recv = Column(Float)
    total_recruiter_paid = Column(Float)
    total_referral_paid = Column(Float)
    last_payment_date = Column(DateTime)

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    role = Column(String)
    location = Column(String)
    candidate_cost = Column(Float)
    phone = Column(String)
    email = Column(String)
    feedback = Column(String(length=None))
    cv_link = Column(String)
    status = Column(String)
    client_id = Column(Integer, ForeignKey('clients.id'))


class SubmitCVRole(Base):
    __tablename__ = 'submit_cv_role'
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    open_roles_id = Column(Integer)
    candidates_id = Column(Integer, ForeignKey('candidates.id'))
    status = Column(String)
    submitted_on = Column(DateTime)
    remote = Column(String)
    cv_link = Column(String)
    test_answers = Column(String)
    test_score = Column(String)
    match_score = Column(String)

class OpenRoles(Base):
    __tablename__ = 'open_roles'
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    role_desc = Column(String)
    location = Column(String)
    status = Column(String)
    posted_on = Column(DateTime)
    remote = Column(String)
    job_desc_link = Column(String)
    test_doc = Column(String)
    jd_doc = Column(String)


    
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    email = Column(String)
    msg_id = Column(String)
    role = Column(String)
    password = Column(String)
    client_id = Column(Integer)

class Cashflow(Base):
    __tablename__ = 'cashflows'
    id = Column(Integer, primary_key=True, autoincrement=True)
    cf_date = Column(String)
    pay_from_id = Column(Integer)
    pay_to_id = Column(Integer)
    cf_value = Column(Float)
    txn_id = Column(Integer)
    balance = Column(Float)

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inv_date = Column(String)
    candidate_id = Column(Integer)
    period_start = Column(String)
    period_end = Column(String)
    txn_id = Column(Integer)
    hours_worked = Column(Float)
    inv_value = Column(Float)
    inv_status = Column(String)

class ClientInvoice(Base):
    __tablename__ = 'client_invoices'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inv_date = Column(String)
    due_date = Column(String)
    period_start = Column(String)
    period_end = Column(String)
    client_id = Column(Integer)
    client_name = Column(String)
    client_contact = Column(String)
    client_email = Column(String)
    client_addr = Column(String)
    client_phone = Column(String)
    explain_str = Column(String)
    inv_html = Column(String)
    inv_hash = Column(String)
    inv_value = Column(Float)
    inv_status = Column(String)

# Database setup
DATABASE_URL = os.getenv("DB_URL") + "?sslmode=require&gssencmode=disable"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

