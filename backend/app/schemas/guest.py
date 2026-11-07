from pydantic import BaseModel


class GuestBootstrapResponse(BaseModel):
    guest_id: str
    token: str
