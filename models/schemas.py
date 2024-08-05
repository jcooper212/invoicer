from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CandidateBase(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    location: Optional[str] = None
    candidate_cost: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    feedback: Optional[str] = None
    cv_link: Optional[str] = None
    status: Optional[str] = None

class CandidateCreate(CandidateBase):
    name: str
    role: str
    location: str
    candidate_cost: float
    phone: str
    email: str

class CandidateUpdate(CandidateBase):
    pass

class Candidate(CandidateBase):
    id: int

    class Config:
        orm_mode: True

class ClientBase(BaseModel):
    name: Optional[str] = None
    client_mgr: Optional[str] = None
    client_email: Optional[str] = None
    client_addr: Optional[str] = None
    client_phone: Optional[str] = None
    payment_freq: Optional[str] = None
    client_type: Optional[str] = None

class ClientCreate(ClientBase):
    name: str
    client_mgr: str
    client_email: str
    client_addr: str
    client_phone: str

class ClientUpdate(ClientBase):
    name: str = None
    client_mgr: str = None
    client_email: str = None
    client_addr: str = None
    client_phone: str = None
    payment_freq: str = None
    client_type: str = None

class Client(ClientBase):
    id: int

    class Config:
        orm_mode: True

class TransactionBase(BaseModel):
    txn_date: Optional[datetime] = None
    candidate_id: Optional[int] = None
    client_id: Optional[int] = None
    recruiter_id: Optional[int] = None
    referral_id: Optional[int] = None
    client_price: Optional[float] = None
    referral_price: Optional[float] = None
    recruiter_price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    num_payments_received: Optional[int] = None
    total_client_recv: Optional[float] = None
    total_recruiter_paid: Optional[float] = None
    total_referral_paid: Optional[float] = None
    last_payment_date: Optional[datetime] = None

class TransactionCreate(TransactionBase):
    txn_date: datetime
    candidate_id: int
    client_id: int
    client_price: float
    start_date: datetime
    end_date: datetime

class TransactionUpdate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int

    class Config:
        orm_mode: True

class CashflowBase(BaseModel):
    cf_date: Optional[str] = None
    pay_from_id: Optional[int] = None
    pay_to_id: Optional[int] = None
    cf_value: Optional[float] = None
    txn_id: Optional[int] = None
    balance: Optional[float] = None

class CashflowCreate(CashflowBase):
    cf_date: str
    pay_from_id: int
    pay_to_id: int
    cf_value: float
    txn_id: int

class CashflowUpdate(CashflowBase):
    pass

class Cashflow(CashflowBase):
    id: int

    class Config:
        orm_mode: True

class InvoiceBase(BaseModel):
    inv_date: Optional[str] = None
    candidate_id: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    txn_id: Optional[int] = None
    hours_worked: Optional[float] = None
    inv_value: Optional[float] = None
    inv_status: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    inv_date: str
    candidate_id: int
    period_start: str
    period_end: str
    txn_id: int
    inv_value: float

class InvoiceUpdate(InvoiceBase):
    pass

class Invoice(InvoiceBase):
    id: int

    class Config:
        orm_mode: True

class ClientInvoiceBase(BaseModel):
    inv_date: Optional[str] = None
    due_date: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    client_email: Optional[str] = None
    client_addr: Optional[str] = None
    client_phone: Optional[str] = None
    explain_str: Optional[str] = None
    inv_html: Optional[str] = None
    inv_hash: Optional[str] = None
    inv_value: Optional[float] = None
    inv_status: Optional[str] = None

class ClientInvoiceCreate(ClientInvoiceBase):
    inv_date: str
    due_date: str
    period_start: str
    period_end: str
    client_id: int
    client_name: str
    client_contact: str
    client_email: str
    client_addr: str
    client_phone: str
    explain_str: str
    inv_html: str
    inv_hash: str
    inv_value: float
    inv_status: str

class ClientInvoiceUpdate(ClientInvoiceBase):
    pass

class ClientInvoice(ClientInvoiceBase):
    id: int

    class Config:
        orm_mode: True

class UserBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    msg_id: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[int] = None

class UserCreate(UserBase):
    name: str
    email: str
    msg_id: str
    role: str
    password: str

class UserUpdate(UserBase):
    pass

class User(UserBase):
    id: int

    class Config:
        orm_mode: True

