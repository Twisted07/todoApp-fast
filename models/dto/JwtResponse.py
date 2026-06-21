from pydantic import BaseModel


class JwtResponse(BaseModel):
  message: str
  access_token: str
  type: str