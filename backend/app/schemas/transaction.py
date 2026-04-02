from pydantic import BaseModel, field_validator
from decimal import Decimal
from datetime import date,datetime
from typing import Optional, Literal

TransactionType = Literal["income", "expense"]

class TransactionCreate(BaseModel):
    account_id: int
    category_id: int
    amount: Decimal
    type: TransactionType
    note: Optional[str] = None
    transaction_date: datetime

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    note: Optional[str] = None
    transaction_date: Optional[datetime] = None

class CategoryInTransaction(BaseModel):
    id:    int
    name:  str
    icon:  str
    color: str

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id:               int
    user_id:          int
    account_id:       Optional[int]
    category_id:      Optional[int]
    category:         Optional[CategoryInTransaction]  # Nested object
    amount:           Decimal
    type:             TransactionType
    note:             Optional[str]
    transaction_date: date
    is_recurring:     bool
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True