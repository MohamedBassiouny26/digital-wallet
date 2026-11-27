



from pydantic import BaseModel, ConfigDict

from app.models.ledger import Side


class EntryCreate(BaseModel):
    transaction_id: int
    account_id: int
    side: Side
    amount: int

class EntryResponse(EntryCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)