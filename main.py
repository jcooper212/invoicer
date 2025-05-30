from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.future import select
import jwt
import hashlib
from typing import Optional, List  # Add this import at the top with other imports

#import pkg_resources
#from pydantic import BaseModel
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import openai
import os
import PyPDF2
import io
from models.models import Candidate as DBCandidate, Client as DBClient, Transaction as DBTransaction, Cashflow as DBCashflow, Invoice as DBInvoice, ClientInvoice as DBClientInvoice, User as DBUser, OpenRoles as DBOpenRoles, SubmitCVRole as DBSubmitCVRole, get_db
from models.schemas import CandidateCreate, ClientCreate, TransactionCreate, CashflowCreate, InvoiceCreate, ClientInvoiceCreate, UserCreate, Candidate, Client, Transaction, Cashflow, Invoice, ClientInvoice, User
from models.schemas import CandidateUpdate, ClientUpdate, TransactionUpdate, CashflowUpdate, InvoiceUpdate, ClientInvoiceUpdate, UserUpdate, OpenRoles, OpenRolesCreate, SubmitCVRole, SubmitCVRoleCreate, OpenRolesUpdate, SubmitCVRoleUpdate
from save_bucket import upload_file, get_file
import random

# Initialize
load_dotenv()
RAYZE_HOST = os.getenv('RAYZE_HOST')
RAYZE_LOCALHOST = os.getenv('RAYZE_LOCALHOST')

# Set API key based on model
model = os.getenv("RAYZE_MODEL", "OPENAI")
if model == "CLAUDE":
    llm_api_key = os.getenv("ANTHROPIC_API_KEY")
    from evaluation.generate_test_claude import generate_candidate_evaluation, generate_candidate_match, generate_score, generate_candidate_cv, generate_job_desc
elif model == "GROK":
    llm_api_key = os.getenv("GROK_API_KEY")
    from evaluation.generate_test_grok import generate_candidate_evaluation, generate_candidate_match, generate_score, generate_candidate_cv, generate_job_desc
else:  # Default to OpenAI
    llm_api_key = os.getenv("OPENAI_API_KEY")
    from evaluation.generate_test import generate_candidate_evaluation, generate_candidate_match, generate_score, generate_candidate_cv, generate_job_desc

from pydantic import BaseModel

# Content Path
PATH_TO_BLOG = Path('.')
PATH_TO_CONTENT = PATH_TO_BLOG/"content"
PATH_TO_CONTENT.mkdir(exist_ok=True, parents=True)
RAYZE_LOGO = PATH_TO_CONTENT/"rayze_logo.jpg"

# JWT Define a secret key (change this to a secure random value in production)
SECRET_KEY = os.getenv("RAYZE_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Allow requests from localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List all packges ---deprecated in py 3.12
# def list_installed_packages():
#     packages = pkg_resources.working_set
#     package_list = sorted(["%s==%s" % (i.key, i.version) for i in packages])
#     return package_list

# @app.get("/packages")
# def get_packages():
#     return list_installed_packages()

    # Authenticataion functions
# Function to generate access token route
@app.post("/generate_token")
async def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user[1]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Function to verify token route
@app.post("/verify_token")
async def verify_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_name: str = payload.get("sub")
    if user_name is None:
        raise credentials_exception
    #token_data = TokenData(username=user_name)
    return token

# Authenticataion functions
@app.post("/authenticate")
async def authenticate(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    # Add user info in a new field, but keep access_token and token_type as before
    user_info = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "client_id": user.client_id
    }
    return {"access_token": access_token, "token_type": "bearer", "user": user_info}

# Function to hash passwords
def get_password_hash(password: str):
    password_bytes = password.encode('utf-8')
    hash_obj = hashlib.sha256()
    hash_obj.update(password_bytes)
    hashed_password = hash_obj.hexdigest()
    return hashed_password

# Function to verify passwords
def verify_password(plain_password, hashed_password):
    #     Verify if a plain text password matches the hashed password.
    hashed_input_password = get_password_hash(plain_password)
    print("plain pwd inp: ", plain_password, "hashed pwd inp: ", hashed_password, "hash(plain_pwd) :", hashed_input_password, "hashOfKey: ",get_password_hash(SECRET_KEY),"key: ", SECRET_KEY)
    if hashed_input_password == hashed_password:
        return True
    else:
        return False


# Function to generate access token
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to authenticate users
def authenticate_user(username: str, password: str):
    db = next(get_db())
    try:
        user_data = find_user_by_name(username, db)
        print('verify ', user_data.name, password, user_data.password)
        if user_data and verify_password(password, user_data.password):
            return user_data  # Return the full user object
    except HTTPException as e:
        print(e.detail)
    finally:
        db.close()
    return None

# Function to save data to the database
def save_data(db, model, data):
    try:
        db_item = model(**data)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
    except SQLAlchemyError as e:
        db.rollback()
        print(f"An error occurred: {str(e)}")

# Function to get all records from a table
def get_all_records(table_name):
    session = SessionLocal()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        results = session.execute(table.select()).fetchall()
        return results
    except SQLAlchemyError as e:
        print(f"Error fetching records: {e}")
    finally:
        session.close()

# Function to update data in the database
def update_data(table_name, record_id, data):
    session = SessionLocal()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        update_values = {key: value for key, value in data.items()}
        session.execute(
            table.update().where(table.c.id == record_id).values(update_values)
        )
        session.commit()
    except SQLAlchemyError as e:
        print(f"Error updating data: {e}")
    finally:
        session.close()

# Function to find a record by ID
def find_record_by_id(table_name, record_id):
    session = SessionLocal()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        result = session.execute(table.select().where(table.c.id == record_id)).fetchone()
        return result
    except SQLAlchemyError as e:
        print(f"Error finding record by ID: {e}")
    finally:
        session.close()

# Function to find a record by field
def find_record_by_field(table_name, field_name, field_value):
    session = SessionLocal()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        result = session.execute(table.select().where(table.c[field_name] == field_value)).fetchall()
        return result
    except SQLAlchemyError as e:
        print(f"Error finding record by field: {e}")
    finally:
        session.close()

# Function to find a record by name
def find_record_by_name(table_name, name):
    session = SessionLocal()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
        result = session.execute(table.select().where(table.c.name == name)).fetchone()
        return result
    except SQLAlchemyError as e:
        print(f"Error finding record by name: {e}")
    finally:
        session.close()

@app.get("/get_client_transactions/{recruiter_id}")
def get_client_transactions(recruiter_id: int, db: Session = Depends(get_db),
        user_name: str = Depends(verify_token)):
    try:
        transactions = (
        db.query(
            DBTransaction.id.label('txn_id'),
            DBCandidate.id.label('candidate_id'),
            DBClient.name.label('client_name'),
            DBCandidate.name.label('candidate_name'),
            DBTransaction.recruiter_price,
            DBTransaction.client_price,
            DBClient.client_mgr.label('client_contact'),
            DBClient.client_email,
            DBClient.client_addr,
            DBClient.client_phone,
            DBClient.id.label('client_id')
            )
            .join(DBClient, DBTransaction.client_id == DBClient.id)
            .join(DBCandidate, DBTransaction.candidate_id == DBCandidate.id)
            .filter(DBTransaction.recruiter_id == recruiter_id)
            .filter(DBCandidate.status == 'Hired')
            .all()
        )
        #print(transactions)
        if not transactions:
            raise HTTPException(status_code=404, detail="No transactions found")
        
                # Convert to a list of dictionaries
        transactions_list = [
            {
                'txn_id': txn_id,
                'candidate_id': candidate_id,
                'client_name': client_name,
                'candidate_name': candidate_name,
                'recruiter_price': recruiter_price,
                'client_price': client_price,
                'client_contact': client_contact,
                'client_email': client_email,
                'client_addr': client_addr,
                'client_phone': client_phone,
                'client_id': client_id
            }
            for txn_id, candidate_id, client_name, candidate_name, recruiter_price, client_price, client_contact, client_email, client_addr, client_phone, client_id in transactions
        ]
        return transactions_list    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_console_activity")
def get_console_activity(db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    try:
        # Calculate date 31 days ago using UTC
        thirty_one_days_ago = datetime.utcnow().replace(tzinfo=None) - timedelta(days=31)
        activity_list = []

        # Query 1: Recent hires
        recent_hires = (
            db.query(
                DBCandidate.name,
                DBTransaction.start_date
            )
            .join(DBTransaction, DBCandidate.id == DBTransaction.candidate_id)
            .filter(DBCandidate.status == 'Hired')
            .filter(DBTransaction.start_date >= thirty_one_days_ago)
            .order_by(DBTransaction.start_date.desc())
            .all()
        )

        # Add hires to activity list
        for name, start_date in recent_hires:
            days_ago = (datetime.utcnow().replace(tzinfo=None) - start_date.replace(tzinfo=None)).days
            activity_list.append({
                'title': 'New Hire',
                'name': name,
                'days_ago': days_ago
            })

        # Query 2: Recent CV submissions
        recent_submissions = (
            db.query(
                DBCandidate.name,
                DBOpenRoles.role_desc,
                DBClient.name.label('client_name'),
                DBSubmitCVRole.submitted_on
            )
            .join(DBSubmitCVRole, DBCandidate.id == DBSubmitCVRole.candidates_id)
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)
            .join(DBClient, DBOpenRoles.client_id == DBClient.id)
            .filter(DBOpenRoles.status == 'Open')
            .filter(DBSubmitCVRole.submitted_on >= thirty_one_days_ago)
            .order_by(DBSubmitCVRole.submitted_on.desc())
            .all()
        )

        # Add submissions to activity list
        for candidate_name, role_desc, client_name, submitted_on in recent_submissions:
            days_ago = (datetime.utcnow().replace(tzinfo=None) - submitted_on.replace(tzinfo=None)).days
            activity_list.append({
                'title': 'Candidate Submitted',
                'name': f"{candidate_name} for {role_desc} at {client_name}",
                'days_ago': days_ago
            })

        # Query 3: Recent open roles
        recent_roles = (
            db.query(
                DBOpenRoles.role_desc,
                DBOpenRoles.posted_on
            )
            .filter(DBOpenRoles.status == 'Open')
            .filter(DBOpenRoles.posted_on >= thirty_one_days_ago)
            .order_by(DBOpenRoles.posted_on.desc())
            .all()
        )

        # Add open roles to activity list
        for role_desc, posted_on in recent_roles:
            days_ago = (datetime.utcnow().replace(tzinfo=None) - posted_on.replace(tzinfo=None)).days
            activity_list.append({
                'title': 'New Open Role',
                'name': role_desc,
                'days_ago': days_ago
            })

        # Sort the entire list by days_ago
        activity_list.sort(key=lambda x: x['days_ago'])

        return activity_list

    except Exception as e:
        print(f"Error in get_console_activity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving console activity: {str(e)}"
        )

@app.get("/get_console_data")
def get_console_data(client_id: Optional[int] = None, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    try:
        # Base query for candidates on payroll (status = Hired)
        payroll_query = db.query(func.count(DBCandidate.id))\
            .filter(DBCandidate.status == 'Hired')
                
        payroll_candidates = payroll_query.scalar()

        # Calculate date 31 days ago
        thirty_one_days_ago = datetime.utcnow() - timedelta(days=31)
        
        # Base query for candidates hired in the last 31 days
        hired_query = db.query(func.count(DBTransaction.id))\
            .filter(DBTransaction.start_date >= thirty_one_days_ago)
        
        hired_last_month = hired_query.scalar()

        # Base query for total submitted CVs for open roles
        submit_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Open')
        
        submit_cvs = submit_query.scalar()

        # Base query for submitted CVs in the last 31 days for open roles
        submit_last_month_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBSubmitCVRole.submitted_on >= thirty_one_days_ago)
        
        submit_last_month = submit_last_month_query.scalar()

        # Base query for total active open roles
        active_roles_query = db.query(func.count(DBOpenRoles.id))\
            .filter(DBOpenRoles.status == 'Open')
        
        
        active_roles = active_roles_query.scalar()

        # Base query for open roles created in the last 31 days
        roles_last_month_query = db.query(func.count(DBOpenRoles.id))\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBOpenRoles.posted_on >= thirty_one_days_ago)
        
        
        roles_last_month = roles_last_month_query.scalar()

        # Base query for most recent invoice date
        max_invoice_query = db.query(func.max(DBInvoice.inv_date))
        
        
        max_invoice_date = max_invoice_query.scalar()

        # Base query for total hours in the most recent invoice month
        invoice_hours = 0
        if max_invoice_date:
            invoice_hours_query = db.query(func.sum(DBInvoice.hours_worked))\
                .filter(DBInvoice.inv_date == max_invoice_date)
            
        
            invoice_hours = invoice_hours_query.scalar() or 0

        return {
            "payroll_candidates": payroll_candidates or 0,
            "hired_last_month": hired_last_month or 0,
            "submit_cvs": submit_cvs or 0,
            "submit_last_month": submit_last_month or 0,
            "active_roles": active_roles or 0,
            "roles_last_month": roles_last_month or 0,
            "max_invoice_date": max_invoice_date if max_invoice_date else None,
            "invoice_hours": invoice_hours
        }
    except Exception as e:
        print(f"Error in get_console_data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving console data: {str(e)}"
        )

@app.get("/get_console_data_by_client/{client_id}")
def get_console_data_by_client(client_id: int, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    try:
        # Base query for candidates on payroll (status = Hired)
        total_client_hires_query = db.query(func.count(DBCandidate.id))\
            .filter(DBCandidate.status == 'Hired')\
            .filter(DBCandidate.client_id == client_id)
                
        total_active_eng = total_client_hires_query.scalar() #return this
        # Calculate date 31 days ago
        thirty_one_days_ago = datetime.utcnow() - timedelta(days=31)

        # Base query for candidates on payroll (status = Hired)
        total_client_hires_query = db.query(func.count(DBCandidate.id))\
            .filter(DBCandidate.status == 'Hired')\
            .filter(DBTransaction.start_date >= thirty_one_days_ago)\
            .filter(DBCandidate.id == DBTransaction.candidate_id)\
            .filter(DBCandidate.client_id == client_id)
        
        total_active_eng_last30 = total_client_hires_query.scalar() #return this


        # Base query for candidates  in the last 31 days
        hired_query = db.query(func.count(DBTransaction.id))\
            .filter(DBTransaction.start_date >= thirty_one_days_ago)\
            .filter(DBTransaction.candidate_id.in_(
                db.query(DBCandidate.id).filter(DBCandidate.client_id == client_id)
            ))
        
        hired_last30 = hired_query.scalar()

        # Base query for total submitted CVs for open roles
        submit_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBOpenRoles.client_id == client_id)
        
        submit_client_cvs = submit_query.scalar()

        # Base query for submitted CVs in the last 31 days for open roles
        submit_last_month_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBSubmitCVRole.submitted_on >= thirty_one_days_ago)\
            .filter(DBSubmitCVRole.candidates_id.in_(
                db.query(DBCandidate.id).filter(DBCandidate.client_id == client_id)
            ))
        
        submit_client_cvs_last30 = submit_last_month_query.scalar() #return this

        # Base query for total active open roles
        active_roles_query = db.query(func.count(DBOpenRoles.id))\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBOpenRoles.client_id == client_id)
        
        
        active_client_roles = active_roles_query.scalar()

        # Base query for open roles created in the last 31 days
        roles_last_month_query = db.query(func.count(DBOpenRoles.id))\
            .filter(DBOpenRoles.status == 'Open')\
            .filter(DBOpenRoles.posted_on >= thirty_one_days_ago)\
            .filter(DBOpenRoles.client_id == client_id)
        
        
        active_client_roles_last30 = roles_last_month_query.scalar() #return this

        # Base query for total submitted CVs for open roles
        submit_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Hired')\
            .filter(DBOpenRoles.client_id == client_id)
        
        hired_client_cvs = submit_query.scalar() #return this

        # Base query for submitted CVs in the last 31 days for open roles
        submit_last_month_query = db.query(func.count(DBSubmitCVRole.id))\
            .join(DBOpenRoles, DBSubmitCVRole.open_roles_id == DBOpenRoles.id)\
            .filter(DBOpenRoles.status == 'Hired')\
            .filter(DBSubmitCVRole.submitted_on >= thirty_one_days_ago)\
            .filter(DBSubmitCVRole.candidates_id.in_(
                db.query(DBCandidate.id).filter(DBCandidate.client_id == client_id)
            ))
        
        hired_client_cvs_last30 = submit_last_month_query.scalar() #return this


        return {
            "total_active_eng": total_active_eng or 0,
            "total_active_eng_last30": total_active_eng_last30 or 0,
            "submit_client_cvs": submit_client_cvs or 0,
            "submit_client_cvs_last30": submit_client_cvs_last30 or 0,
            "active_client_roles": active_client_roles or 0,
            "active_client_roles_last30": active_client_roles_last30 or 0,
            "hired_client_cvs": hired_client_cvs or 0,
            "hired_client_cvs_last30": hired_client_cvs_last30 or 0,
        }
    except Exception as e:
        print(f"Error in get_console_data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving console data: {str(e)}"
        )


# Function to handle new candidate creation
@app.post("/new_candidate", response_model=Candidate)
def create_candidate(candidate: CandidateCreate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    
    candidate_data = DBCandidate(**candidate.dict())
    print(candidate_data)
    db.add(candidate_data)
    db.commit()
    db.refresh(candidate_data)
    return candidate_data


# Function to handle new client creation
@app.post("/new_client", response_model=Client)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    client_data = DBClient(**client.dict())
    db.add(client_data)
    db.commit()
    db.refresh(client_data)
    return client_data

# Function to handle new transaction creation
@app.post("/new_transaction", response_model=Transaction)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    transaction_data = DBTransaction(**transaction.dict())
    db.add(transaction_data)
    db.commit()
    db.refresh(transaction_data)
    return transaction_data

# Function to handle new cashflow creation
@app.post("/new_cashflow", response_model=Cashflow)
def create_cashflow(cashflow: CashflowCreate, db: Session = Depends(get_db)):
    cashflow_data = DBCashflow(**cashflow.dict())
    db.add(cashflow_data)
    db.commit()
    db.refresh(cashflow_data)
    return cashflow_data

# Function to handle new invoice creation
@app.post("/new_invoice", response_model=Invoice)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)):
    invoice_data = DBInvoice(**invoice.dict())
    db.add(invoice_data)
    db.commit()
    db.refresh(invoice_data)
    return invoice_data

# Function to handle new client invoice creation
@app.post("/new_client_invoice", response_model=ClientInvoice)
def create_client_invoice(invoice: ClientInvoiceCreate, db: Session = Depends(get_db)):
    client_invoice_data = DBClientInvoice(**invoice.dict())
    db.add(client_invoice_data)
    db.commit()
    db.refresh(client_invoice_data)
    return client_invoice_data

# Function to handle new user creation
@app.post("/new_user", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    user_data = DBUser(**user.dict())
    db.add(user_data)
    db.commit()
    db.refresh(user_data)
    return user_data

# Function to handle new open role creation
@app.post("/new_open_role", response_model=OpenRoles)
def create_open_role(open_role: OpenRolesCreate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    # Convert posted_on string to datetime
    open_role_dict = open_role.dict()
    #open_role_dict['posted_on'] = datetime.strptime(open_role_dict['posted_on'], '%Y-%m-%dT%H:%M:%S.%fZ')
    print('dict ',open_role_dict)
    open_role_data = DBOpenRoles(**open_role_dict)
    db.add(open_role_data)
    db.commit()
    db.refresh(open_role_data)
    return open_role_data

# Function to handle new CV role submission
@app.post("/new_submit_cvrole",response_model=SubmitCVRole)
async def create_submit_cvrole(
    submit_cvrole: SubmitCVRoleCreate, 
    db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)
):
    """Create a new CV role submission"""
    try:
        submit_cvrole_data = DBSubmitCVRole(**submit_cvrole.dict())
        db.add(submit_cvrole_data)
        db.commit()
        db.refresh(submit_cvrole_data)
        return {
            key: value 
            for key, value in submit_cvrole_data.__dict__.items() 
            if not key.startswith('_')
        }
    except Exception as e:
        db.rollback()
        print(f"Error creating submit_cvrole: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error creating submission: {str(e)}"
        )

# Function to list all candidates
@app.get("/list_candidates")
def list_candidates(db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    candidates = db.query(DBCandidate).all()
    return candidates

# Function to list all clients
@app.get("/list_clients")
def list_clients(db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    clients = db.query(DBClient).all()
    return clients

# Function to list all transactions
@app.get("/list_transactions")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.query(DBTransaction).all()
    return transactions

# Function to list all cashflows
@app.get("/list_cashflows")
def list_cashflows(db: Session = Depends(get_db)):
    cashflows = db.query(DBCashflow).all()
    return cashflows

# Function to list all invoices
@app.get("/list_invoices")
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(DBInvoice).all()
    return invoices

# Function to list all client invoices
@app.get("/list_client_invoices")
def list_client_invoices(db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)):
    ##client_invoices = db.query(DBClientInvoice).all()
    client_invoices = db.query(DBClientInvoice).order_by(DBClientInvoice.inv_date.desc()).all()
    return client_invoices

# Function to list all users
@app.get("/list_users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(DBUser).all()
    return users

@app.get("/list_open_roles")
def list_open_roles(db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    open_roles = db.query(DBOpenRoles).all()
    return open_roles

# Function to list all CV role submissions
@app.get("/list_submit_cvroles")
def list_submit_cvroles(db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    submit_cvroles = db.query(DBSubmitCVRole).all()
    return submit_cvroles

# Function to update a candidate
@app.put("/update_candidate/{candidate_id}")
def update_candidate(candidate_id: int, candidate: CandidateUpdate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    candidate_to_update = db.query(DBCandidate).filter(DBCandidate.id == candidate_id).first()
    if not candidate_to_update:
        raise HTTPException(status_code=404, detail="Candidate not found")

    for key, value in candidate.dict(exclude_unset=True).items():
        setattr(candidate_to_update, key, value)
    
    db.commit()
    db.refresh(candidate_to_update)
    return {"message": "Candidate updated successfully"}

# Function to update a client
@app.put("/update_client/{client_id}")
def update_client(client_id: int, client: ClientUpdate, db: Session = Depends(get_db)):
    client_to_update = db.query(DBClient).filter(DBClient.id == client_id).first()
    if not client_to_update:
        raise HTTPException(status_code=404, detail="Client not found")

    for key, value in client.dict(exclude_unset=True).items():
        setattr(client_to_update, key, value)
    
    db.commit()
    db.refresh(client_to_update)
    return {"message": "Client updated successfully"}

# Function to update a transaction
@app.put("/update_transaction/{transaction_id}")
def update_transaction(transaction_id: int, transaction: TransactionUpdate, db: Session = Depends(get_db)):
    transaction_to_update = db.query(DBTransaction).filter(DBTransaction.id == transaction_id).first()
    if not transaction_to_update:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for key, value in transaction.dict(exclude_unset=True).items():
        setattr(transaction_to_update, key, value)
    
    db.commit()
    db.refresh(transaction_to_update)
    return {"message": "Transaction updated successfully"}

# Function to update a cashflow
@app.put("/update_cashflow/{cashflow_id}")
def update_cashflow(cashflow_id: int, cashflow: CashflowUpdate, db: Session = Depends(get_db)):
    cashflow_to_update = db.query(DBCashflow).filter(DBCashflow.id == cashflow_id).first()
    if not cashflow_to_update:
        raise HTTPException(status_code=404, detail="Cashflow not found")

    for key, value in cashflow.dict(exclude_unset=True).items():
        setattr(cashflow_to_update, key, value)
    
    db.commit()
    db.refresh(cashflow_to_update)
    return {"message": "Cashflow updated successfully"}

# Function to update an invoice
@app.put("/update_invoice/{invoice_id}")
def update_invoice(invoice_id: int, invoice: InvoiceUpdate, db: Session = Depends(get_db)):
    invoice_to_update = db.query(DBInvoice).filter(DBInvoice.id == invoice_id).first()
    if not invoice_to_update:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for key, value in invoice.dict(exclude_unset=True).items():
        setattr(invoice_to_update, key, value)
    
    db.commit()
    db.refresh(invoice_to_update)
    return {"message": "Invoice updated successfully"}

# Function to update a client invoice
@app.put("/update_client_invoice/{invoice_id}")
def update_client_invoice(invoice_id: int, invoice: ClientInvoiceUpdate, db: Session = Depends(get_db)):
    client_invoice_to_update = db.query(DBClientInvoice).filter(DBClientInvoice.id == invoice_id).first()
    if not client_invoice_to_update:
        raise HTTPException(status_code=404, detail="Client Invoice not found")

    for key, value in invoice.dict(exclude_unset=True).items():
        setattr(client_invoice_to_update, key, value)
    
    db.commit()
    db.refresh(client_invoice_to_update)
    return {"message": "Client Invoice updated successfully"}

# Function to update a user
@app.put("/update_user/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    user_to_update = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict(exclude_unset=True).items():
        setattr(user_to_update, key, value)
    
    db.commit()
    db.refresh(user_to_update)
    return {"message": "User updated successfully"}

@app.put("/update_open_role/{role_id}", response_model=OpenRoles)
def update_open_role(
    role_id: int, 
    role_update: OpenRolesUpdate, 
    db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)
):
    # First, get the existing role
    db_role = db.query(DBOpenRoles).filter(DBOpenRoles.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Open role not found")

    # Update the role's attributes
    update_data = role_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_role, key, value)

    try:
        db.commit()
        db.refresh(db_role)
        return db_role
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/find_candidate/{candidate_id}")
def find_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(DBCandidate).filter(DBCandidate.id == candidate_id).first()
    if candidate:
        return candidate
    else:
        raise HTTPException(status_code=404, detail="Candidate not found")

# Function to find a client by ID
@app.get("/find_client/{client_id}")
def find_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(DBClient).filter(DBClient.id == client_id).first()
    if client:
        return client
    else:
        raise HTTPException(status_code=404, detail="Client not found")

# Function to find a transaction by ID
@app.get("/find_transaction/{transaction_id}")
def find_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(DBTransaction).filter(DBTransaction.id == transaction_id).first()
    if transaction:
        return transaction
    else:
        raise HTTPException(status_code=404, detail="Transaction not found")

# Function to find a cashflow by ID
@app.get("/find_cashflow/{cashflow_id}")
def find_cashflow(cashflow_id: int, db: Session = Depends(get_db)):
    cashflow = db.query(DBCashflow).filter(DBCashflow.id == cashflow_id).first()
    if cashflow:
        return cashflow
    else:
        raise HTTPException(status_code=404, detail="Cashflow not found")

# Function to find an invoice by ID
@app.get("/find_invoice/{invoice_id}")
def find_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(DBInvoice).filter(DBInvoice.id == invoice_id).first()
    if invoice:
        return invoice
    else:
        raise HTTPException(status_code=404, detail="Invoice not found")

# Function to find a client invoice by ID
@app.get("/find_client_invoice/{invoice_id}")
def find_client_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(DBClientInvoice).filter(DBClientInvoice.id == invoice_id).first()
    if invoice:
        return invoice
    else:
        raise HTTPException(status_code=404, detail="Client Invoice not found")

# Function to find a client invoice by client ID
@app.get("/find_invoice_client_id/{client_id}")
def find_invoice_by_client_id(client_id: int, db: Session = Depends(get_db)):
    invoices = db.query(DBClientInvoice).filter(DBClientInvoice.client_id == client_id).all()
    if invoices:
        return invoices
    else:
        raise HTTPException(status_code=404, detail="Client Invoices not found")

# Function to find a user by ID
@app.get("/find_user/{user_id}")
def find_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Function to find a candidate by name
@app.get("/find_candidate_by_name/{name}")
def find_candidate_by_name(name: str, db: Session = Depends(get_db)):
    candidate = db.query(DBCandidate).filter(DBCandidate.name == name).first()
    if candidate:
        return candidate
    else:
        raise HTTPException(status_code=404, detail="Candidate not found")

@app.get("/find_candidate_by_client/{client_id}")
def find_candidate_by_client(client_id: int, db: Session = Depends(get_db)):
    try:
        # First verify the client exists
        client = db.query(DBClient).filter(DBClient.id == client_id).first()
        if not client:
            return []  # Return empty list if client doesn't exist
            
        # Get candidates for the client
        candidates = db.query(DBCandidate).filter(DBCandidate.client_id == client_id).all()
        return candidates or []  # Return empty list if no candidates found
    except Exception as e:
        print(f"Error in find_candidate_by_client: {str(e)}")
        return []  # Return empty list on any error


# Function to find a user by name
@app.get("/find_user_by_name/{user_name}")
def find_user_by_name(user_name: str, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.name == user_name).first()
    if user:
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")

# Function to find transactions for a given client ID
@app.get("/find_my_candidates/{client_id}")
def find_my_candidates(client_id: int, db: Session = Depends(get_db)):
    transactions = db.query(DBTransaction).filter(DBTransaction.client_id == client_id).all()
    if transactions:
        return transactions
    else:
        raise HTTPException(status_code=404, detail="Transactions not found")

# Function to find the latest invoice by client ID
@app.get("/find_latest_invoice/{client_id}")
def find_latest_invoice(client_id: str, db: Session = Depends(get_db)):
    latest_invoice = db.query(DBInvoice.inv_date, func.max(DBInvoice.id))\
                       .filter(DBInvoice.client_id == client_id)\
                       .first()

    if latest_invoice:
        inv_date, _ = latest_invoice
        return {"inv_date": inv_date}
    else:
        raise HTTPException(status_code=404, detail="Invoice not found")

@app.get("/find_open_roles/{client_id}")
def find_open_roles_by_client(
    client_id: int, 
    db: Session = Depends(get_db)
):
    """
    Find all open roles associated with a specific client ID.
    Returns an empty list if no roles are found.
    """
    try:
        # Verify client exists first
        client = db.query(DBClient).filter(DBClient.id == client_id).first()
        if not client:
            return []

        # Query open roles and convert to dict to avoid validation issues
        open_roles = db.query(DBOpenRoles)\
            .filter(DBOpenRoles.client_id == client_id)\
            .order_by(DBOpenRoles.posted_on.desc())\
            .all()
        
        # Convert to dictionary list and exclude None values
        return [
            {
                key: value 
                for key, value in role.__dict__.items() 
                if not key.startswith('_') and value is not None
            }
            for role in open_roles
        ] or []
        
    except Exception as e:
        print(f"Error in find_open_roles_by_client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error occurred: {str(e)}"
        )
    finally:
        db.close()

@app.get("/find_submit_cvrole/{open_roles_id}", response_model=list[SubmitCVRole])
def find_submit_cvrole_by_role(
    open_role_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)
):
    """
    Find all CV submissions for a specific open role ID.
    Optionally filter by status.
    Returns an empty list if no submissions are found.
    """
    try:
        # First verify the open role exists
        open_role = db.query(DBOpenRoles)\
            .filter(DBOpenRoles.id == open_role_id)\
            .first()
            
        if not open_role:
            raise HTTPException(
                status_code=404,
                detail=f"Open role with ID {open_role_id} not found"
            )

        # Build the query for CV submissions
        query = db.query(DBSubmitCVRole)\
            .filter(DBSubmitCVRole.role_id == open_role_id)\
            .order_by(DBSubmitCVRole.created_at.desc())

        # Add status filter if provided
        if status:
            query = query.filter(DBSubmitCVRole.status == status)

        submissions = query.all()
        
        if not submissions:
            return []
            
        return submissions
        
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error occurred: {str(e)}"
        )

class WorkOrderResponse(BaseModel):
    html: str

@app.post("/generate_client_work_order", response_model=WorkOrderResponse)
def generate_client_work_order(transaction: TransactionCreate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    transaction_data = DBTransaction(**transaction.dict())
    txn_html = create_html_work_order(transaction_data, db)
    return WorkOrderResponse(html=txn_html)


# Submit client invoice
@app.post("/submit_client_invoice")
def submit_client_invoice(invoice: ClientInvoiceCreate, db: Session = Depends(get_db),
    user_name: str = Depends(verify_token)):
    invoice_data = DBClientInvoice(**invoice.dict())    
    db.add(invoice_data)
    db.commit()
    db.refresh(invoice_data)

    # Extract the client invoice id
    inv_id = db.query(func.max(DBClientInvoice.id))\
               .filter(DBClientInvoice.inv_date == invoice.inv_date,
                       DBClientInvoice.client_id == invoice.client_id)\
               .scalar()

    if inv_id:
        # Update invoice HTML and hash
        invoice.inv_html = create_html_invoice(inv_id, invoice, db)
        invoice.inv_hash = get_password_hash(f"{inv_id}_{invoice.client_id}_{invoice.inv_date}")

        db.query(DBClientInvoice)\
          .filter(DBClientInvoice.id == inv_id)\
          .update({"inv_html": invoice.inv_html, "inv_hash": invoice.inv_hash})
        db.commit()

        return {"inv_html": invoice.inv_html}
    else:
        raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/generate_invoices/{transaction_id}")
def generate_invoices(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    start_date = datetime.strptime(transaction.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(transaction.end_date, '%Y-%m-%d')
    num_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1

    invoices_written = 0
    for i in range(num_months):
        inv_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)  # Last day of the month
        period_start = start_date
        period_end = inv_date
        hours_worked = 160  # Default hours worked
        inv_value = transaction.client_price * hours_worked
        inv_status = "PRE"

        invoice_data = {
            "inv_date": inv_date.strftime('%Y-%m-%d'),
            "candidate_id": transaction.candidate_id,
            "period_start": period_start.strftime('%Y-%m-%d'),
            "period_end": period_end.strftime('%Y-%m-%d'),
            "txn_id": transaction.id,
            "hours_worked": hours_worked,
            "inv_value": inv_value,
            "inv_status": inv_status
        }

        new_invoice = Invoice(**invoice_data)
        db.add(new_invoice)
        db.commit()
        invoices_written += 1

        # Move start_date to the next month
        start_date = start_date + timedelta(days=32)

    return {"invoices_written": invoices_written}


 #Register
@app.post("/register")
async def register(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_data = {
        "name": form_data.username,
        "email": form_data.username,
        "role": "CLIENT",
        "password": get_password_hash(form_data.password),
        "client_id": 0
    }
    db.add(User(**user_data))
    db.commit()
    return {"message": "User registered successfully"}

# Get Invoice
@app.get("/get_invoice/{id_str}")
def get_invoice(id_str: str, db: Session = Depends(get_db)):
    try:
        invoice = db.execute(select(DBClientInvoice.inv_html).filter(DBClientInvoice.inv_hash == id_str)).scalars().one()
        return {"html": invoice}
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Invoice not found")

# @app.get("/get_invoice/{id_str}")
# def get_invoice(id_str: str, db: Session = Depends(get_db),
#     user_name: str = Depends(verify_token)):
#     try:
#         # Retrieve the filename from the database
#         stmt = select(DBInvoice.inv_html).filter(DBInvoice.inv_hash == id_str)
#         result = db.execute(stmt)
#         inv_html = result.scalar_one()
#         return {"html": inv_html}

        # filename = result.scalar_one()
        
        # # Construct the full file path
        # file_path = os.path.join("./", filename)
        
        # # Read the file contents
        # if os.path.exists(file_path):
        #     with open(file_path, 'r') as file:
        #         file_contents = file.read()
        #     return {"html": file_contents}
        # else:
        #     raise HTTPException(status_code=404, detail="File not found")
        
    # except NoResultFound:
    #     raise HTTPException(status_code=404, detail="Invoice not found")

def create_html_invoice(inv_id: int, invoice: ClientInvoice, db: Session = Depends(get_db)) -> str:
    # Fetch the invoice details from the database
    #invoice = db.query(DBClientInvoice).filter(DBClientInvoice.id == inv_id).first()
    
    if not invoice:
        raise ValueError("Invoice not found")

    # Prepare the HTML content
    path_to_template = PATH_TO_CONTENT / "invoice_template.html"
    
    # Read the template
    with open(path_to_template, 'r') as file:
        html_content = file.read()
        
        html_content = html_content.replace("total_due", f"${invoice.inv_value:,.2f}")
        html_content = html_content.replace("due_date", invoice.due_date)
        html_content = html_content.replace("start_date", invoice.period_start)
        html_content = html_content.replace("end_date", invoice.period_end)
        html_content = html_content.replace("invoice_title", "Technology Services")
        html_content = html_content.replace("invoice_num", str(inv_id))
        html_content = html_content.replace("invoice_date", invoice.inv_date)
        html_content = html_content.replace("client_name", invoice.client_name)
        # html_content = html_content.replace("client_contact", invoice.client_contact)
        html_content = html_content.replace("invoice_table", invoice.explain_str)
        html_content = html_content.replace("rayze_logo", RAYZE_LOGO.as_posix())
    
    # Paths for new content
    new_title = f"Inv_{invoice.client_name}_{inv_id}.html"
    new_title_pdf = f"Inv_{invoice.client_name}_{inv_id}.pdf"
    
    path_to_new_content = PATH_TO_CONTENT / new_title
    path_to_new_pdf = PATH_TO_CONTENT / new_title_pdf
    print(path_to_new_content)
       #print(path_to_new_content, " : ",html_content)
    # Save the HTML content to a file
    with open(path_to_new_content, 'w') as file:
        file.write(html_content)

    
    
    # Return the path to the HTML file
    return str(html_content)

def create_html_work_order(transaction: Transaction, db: Session = Depends(get_db)) -> str:
    if not transaction:
        raise ValueError("Transaction not found")

    # Prepare the HTML content
    path_to_template = PATH_TO_CONTENT / "client_work_order.html"
    
    # Read the template
    with open(path_to_template, 'r') as file:
        html_content = file.read()
        
        # Get candidate name from database
        candidate = db.query(DBCandidate).filter(DBCandidate.id == transaction.candidate_id).first()
        if not candidate:
            raise ValueError("Candidate not found")
            
        # Get client details from database
        client = db.query(DBClient).filter(DBClient.id == transaction.client_id).first()
        if not client:
            raise ValueError("Client not found")
        
        # Format dates as strings
        txn_date = transaction.txn_date.strftime('%Y-%m-%d') if transaction.txn_date else ''
        start_date = transaction.start_date.strftime('%Y-%m-%d') if transaction.start_date else ''
        end_date = transaction.end_date.strftime('%Y-%m-%d') if transaction.end_date else ''
        
        # Replace placeholders with actual data
        html_content = html_content.replace("client_name", client.name)
        html_content = html_content.replace("txn_date", txn_date)
        html_content = html_content.replace("candidate_name", candidate.name)
        html_content = html_content.replace("start_date", start_date)
        html_content = html_content.replace("end_date", end_date)
        html_content = html_content.replace("client_rate", f"${transaction.client_price:,.2f}")
        html_content = html_content.replace("client_contact", client.client_mgr)
        html_content = html_content.replace("rayze_logo", RAYZE_LOGO.as_posix())
    
    # Paths for new content

    new_title = f"WO_{client.name}_{txn_date}_{generate_fixed_random()}.html"
    
    path_to_new_content = PATH_TO_CONTENT / new_title
    
    # Save the HTML content to a file
    with open(path_to_new_content, 'w') as file:
        file.write(html_content)
    
    # Upload the file to Supabase
    uploaded_filename = upload_file(html_content, new_title)

    if uploaded_filename:
        return str(html_content)
    else:
        raise HTTPException(status_code=500, detail="Failed to upload file to bucket")


# # Run the FastAPI server
if __name__ == "__main__":
    import uvicorn
    run_port = int(os.getenv("PORT", 8000))  # Default to 8000 if PORT is not set
    run_host = RAYZE_HOST
    uvicorn.run(app, host=run_host, port=run_port)

class JobDescription(BaseModel):
    content: str

class CandidateMatchRequest(BaseModel):
    job_description: str
    candidate_cv: str

class TestScoreRequest(BaseModel):
    test_doc: str
    test_answers: str

@app.post("/generate_candidate_evaluation")
async def create_candidate_evaluation(
    job_description: JobDescription,
    user_name: str = Depends(oauth2_scheme)
):
    """
    Generate a candidate evaluation test based on the provided job description.
    """
    print(job_description.content)
    try:
        if not llm_api_key:
            raise ValueError(f"{model} API key is not set")
        print(job_description.content)

        if model == "grok":
            result = generate_candidate_evaluation(job_description.content, llm_api_key)
        else:
            result = generate_candidate_evaluation(job_description.content)

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating evaluation: {result['message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.post("/generate_score")
async def create_test_score(
    score_request: TestScoreRequest,
    user_name: str = Depends(oauth2_scheme)
):
    """
    Generate a score evaluation based on the test document and candidate's answers.
    """
    try:
        if not llm_api_key:
            raise ValueError(f"{model} API key is not set")

        if model == "grok":
            result = generate_score(score_request.test_doc, score_request.test_answers, llm_api_key)
        else:
            result = generate_score(score_request.test_doc, score_request.test_answers)

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating score: {result['message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.post("/generate_candidate_match")
async def create_candidate_match(
    cv: UploadFile = File(...),
    job_desc: str = Form(...),
    user_name: str = Depends(oauth2_scheme)
):
    """
    Generate a candidate match evaluation based on the provided job description and CV.
    """
    try:
        if not llm_api_key:
            raise ValueError(f"{model} API key is not set")

        # Read the CV file content
        cv_content = await cv.read()
        try:
            cv_text = cv_content.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, try to read as binary and extract text
            pdf_file = io.BytesIO(cv_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            cv_text = ""
            for page in pdf_reader.pages:
                cv_text += page.extract_text() + "\n"

        if model == "grok":
            result = generate_candidate_match(job_desc, cv_text, llm_api_key)
        else:
            result = generate_candidate_match(job_desc, cv_text)

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating match: {result['message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.post("/extract_pdf_text")
async def extract_pdf_text(
    file: UploadFile = File(...),
    user_name: str = Depends(oauth2_scheme)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Create a PDF reader object
        pdf_file = io.BytesIO(contents)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return {
            "status": "success",
            "text": text
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}"
        )

# Function to update a submit CV role
@app.put("/update_submit_cvrole/{cvrole_id}")
def update_submit_cvrole(cvrole_id: int, cvrole: SubmitCVRoleUpdate, db: Session = Depends(get_db), user_name: str = Depends(verify_token)):
    cvrole_to_update = db.query(DBSubmitCVRole).filter(DBSubmitCVRole.id == cvrole_id).first()
    if not cvrole_to_update:
        raise HTTPException(status_code=404, detail="Submit CV Role not found")

    for key, value in cvrole.dict(exclude_unset=True).items():
        setattr(cvrole_to_update, key, value)
    
    db.commit()
    db.refresh(cvrole_to_update)
    return {"message": "Submit CV Role updated successfully"}

@app.post("/generate_candidate")
async def generate_candidate(
    cv: UploadFile = File(...),
    user_name: str = Depends(oauth2_scheme)
):
    """
    Generate a structured JSON object containing key information extracted from a candidate's CV.
    """
    try:

        # Read the CV file content
        cv_content = await cv.read()
        try:
            cv_text = cv_content.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, try to read as binary and extract text
            pdf_file = io.BytesIO(cv_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            cv_text = ""
            for page in pdf_reader.pages:
                cv_text += page.extract_text() + "\n"
  
        if model == "grok":
            result = generate_candidate_cv(cv_text, llm_api_key)
        else:   
            result = generate_candidate_cv(cv_text)

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating candidate info: {result['message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

@app.post("/generate_job_description")
async def generate_job_description(
    job_desc: UploadFile = File(...),
    user_name: str = Depends(oauth2_scheme)
):
    try:

        # Read the jd file content
        jd_content = await job_desc.read()
        try:
            jd_text = jd_content.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 fails, try to read as binary and extract text
            pdf_file = io.BytesIO(jd_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            jd_text = ""
            for page in pdf_reader.pages:
                jd_text += page.extract_text() + "\n"
        print(jd_text)
        if model == "grok":
            result = generate_job_desc(jd_text, llm_api_key)
        else:   
            result = generate_job_desc(jd_text)

        if result["status"] == "success":
            return result
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating job description info: {result['message']}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

def generate_url_safe_hash(data):
    # Create a SHA-256 hash
    hash_object = hashlib.sha256(data.encode('utf-8'))
    # Get the hexadecimal representation (URL-safe: only 0-9, a-f)
    hex_hash = hash_object.hexdigest()
    return hex_hash

@app.post("/store_bucket")
async def store_bucket(
    file: UploadFile = File(...),  # Expect a file upload
    user_name: str = Depends(oauth2_scheme)  # Extract token from Authorization header
):
    """
    Args:
        file (UploadFile): The file to store
        token (str): The OAuth2 token for authentication

    Returns:
        dict: A dictionary containing the status and the uploaded filename
    """
    try:
        # Read the file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        # Get the filename
        filename = generate_url_safe_hash(file.filename)
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Debug logging
        print(f"File type: {type(content)}")
        print(f"Content length: {len(content)}")
        print(f"Filename: {filename}")

        # Upload the file to Supabase
        uploaded_filename = upload_file(content, filename)

        if uploaded_filename:
            return {
                "status": "success",
                "message": "File uploaded successfully to bucket",
                "filename": uploaded_filename
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file to bucket")

    except Exception as e:
        print(f"Error in store_bucket: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    finally:
        await file.close()

@app.get("/read_bucket")
async def read_bucket(
    filename: str,
    user_name: str = Depends(oauth2_scheme)
):
    """
    Read a file from the bucket.
    
    Args:
        filename (str): The name of the file to read from the bucket
        
    Returns:
        dict: A dictionary containing the status and the file content
    """
    try:
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
            
        file_content = get_file(filename)
        
        if file_content:
            # Return the binary content directly
            return {
                "status": "success",
                "message": "File retrieved successfully from bucket",
                "content": file_content  # Return binary content as is
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"File {filename} not found in bucket"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )

def generate_fixed_random():
    random.seed(0)
    return random.randint(100000, 999999)

