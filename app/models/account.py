from pydantic import BaseModel, ConfigDict


class Account(BaseModel):
    id: int
    name: str
    type: str
    normal_side: str
    user_id: int | None

    model_config = ConfigDict(from_attributes=True)

class AccountBalance(BaseModel):
    balance: int
    id: int

    model_config = ConfigDict(from_attributes=True)