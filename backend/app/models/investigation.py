from pydantic import BaseModel


class InvestigationResponse(BaseModel):
    investigation_id: str
    filename: str
    file_type: str
    file_size: int
    sha256: str
