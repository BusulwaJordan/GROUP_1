# ================================
# Domain Layer
# ================================
from datetime import datetime
from enum import Enum
import uuid

class AccountStatus(Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"

class AccountType(Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"

class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"

class Account:
    def __init__(self, account_type: AccountType, initial_deposit=0.0):
        self.account_id = str(uuid.uuid4())
        self.account_type = account_type
        self.balance = initial_deposit
        self.status = AccountStatus.ACTIVE
        self.creation_date = datetime.now()

    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount

    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if self.balance < amount:
            raise ValueError("Insufficient balance.")
        self.balance -= amount

class Transaction:
    def __init__(self, account_id: str, transaction_type: TransactionType, amount: float):
        self.transaction_id = str(uuid.uuid4())
        self.account_id = account_id
        self.transaction_type = transaction_type
        self.amount = amount
        self.timestamp = datetime.now()


# ================================
# Infrastructure Layer
# ================================
class AccountRepository:
    def __init__(self):
        self.accounts = {}

    def create_account(self, account: Account):
        self.accounts[account.account_id] = account
        return account.account_id

    def get_account_by_id(self, account_id: str):
        return self.accounts.get(account_id)

    def update_account(self, account: Account):
        self.accounts[account.account_id] = account

class TransactionRepository:
    def __init__(self):
        self.transactions = []

    def save_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)
        return transaction.transaction_id

    def get_transactions_for_account(self, account_id: str):
        return [tx for tx in self.transactions if tx.account_id == account_id]


# ================================
# Application Layer
# ================================
class AccountCreationService:
    def __init__(self, account_repo: AccountRepository):
        self.account_repo = account_repo

    def create_account(self, account_type: str, initial_deposit=0.0):
        acc_type = AccountType(account_type)
        account = Account(acc_type, initial_deposit)
        self.account_repo.create_account(account)
        return account.account_id

class TransactionService:
    def __init__(self, account_repo: AccountRepository, transaction_repo: TransactionRepository):
        self.account_repo = account_repo
        self.transaction_repo = transaction_repo

    def deposit(self, account_id: str, amount: float):
        account = self.account_repo.get_account_by_id(account_id)
        if not account:
            raise ValueError("Account not found.")
        account.deposit(amount)
        self.account_repo.update_account(account)
        transaction = Transaction(account_id, TransactionType.DEPOSIT, amount)
        self.transaction_repo.save_transaction(transaction)
        return transaction

    def withdraw(self, account_id: str, amount: float):
        account = self.account_repo.get_account_by_id(account_id)
        if not account:
            raise ValueError("Account not found.")
        account.withdraw(amount)
        self.account_repo.update_account(account)
        transaction = Transaction(account_id, TransactionType.WITHDRAW, amount)
        self.transaction_repo.save_transaction(transaction)
        return transaction


# ================================
# Presentation Layer (FastAPI)
# ================================
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Initialize Repos and Services
account_repo = AccountRepository()
transaction_repo = TransactionRepository()
account_service = AccountCreationService(account_repo)
transaction_service = TransactionService(account_repo, transaction_repo)

class AccountRequest(BaseModel):
    accountType: str
    initialDeposit: float = 0.0

class TransactionRequest(BaseModel):
    amount: float

@app.post("/accounts")
def create_account(req: AccountRequest):
    try:
        account_id = account_service.create_account(req.accountType.upper(), req.initialDeposit)
        return {"accountId": account_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/accounts/{account_id}/deposit")
def deposit(account_id: str, req: TransactionRequest):
    try:
        tx = transaction_service.deposit(account_id, req.amount)
        account = account_repo.get_account_by_id(account_id)
        return {
            "transactionId": tx.transaction_id,
            "transactionType": tx.transaction_type.value,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "newBalance": account.balance
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/accounts/{account_id}/withdraw")
def withdraw(account_id: str, req: TransactionRequest):
    try:
        tx = transaction_service.withdraw(account_id, req.amount)
        account = account_repo.get_account_by_id(account_id)
        return {
            "transactionId": tx.transaction_id,
            "transactionType": tx.transaction_type.value,
            "amount": tx.amount,
            "timestamp": tx.timestamp,
            "newBalance": account.balance
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: str):
    account = account_repo.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "accountId": account.account_id,
        "accountType": account.account_type.value,
        "balance": account.balance,
        "status": account.status.value,
        "creationDate": account.creation_date
    }

@app.get("/accounts/{account_id}/transactions")
def get_transactions(account_id: str):
    transactions = transaction_repo.get_transactions_for_account(account_id)
    return [
        {
            "transactionId": t.transaction_id,
            "type": t.transaction_type.value,
            "amount": t.amount,
            "timestamp": t.timestamp
        }
        for t in transactions
    ]
