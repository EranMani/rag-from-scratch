"""
Pydantic schemas — the data contracts between the client and the auth system.

These schemas validate and shape every piece of data entering and leaving the API.
If the payload doesn't match the schema, FastAPI returns a 422 Unprocessable Entity
automatically — preventing malformed data from ever reaching the RAG pipeline or
the knowledge-assessment logic.

How the schemas connect the auth modules together:
    1. Router receives a request validated against RegisterBody / LoginBody.
    2. Validated fields pass to password.py for hashing.
    3. The result is stored via db.py.
    4. The response is serialized through TokenResponse or UserPublic.

Engineering value (Type Safety at the boundary):
    Pydantic enforces types at runtime — the same role TypedDict plays for
    AgentState inside the graph. By catching invalid data at the HTTP edge,
    the agent always operates on clean, well-shaped input. No garbage-in,
    no garbage-out.
"""


from pydantic import BaseModel, EmailStr, Field


class RegisterBody(BaseModel):
    """Inbound payload for user registration.

    EmailStr validates format (must contain @, valid domain structure).
    Password length is bounded to prevent both trivially short and
    denial-of-service-length inputs from reaching bcrypt.
    """
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)


class LoginBody(BaseModel):
    """Inbound payload for login — no length constraint because we only verify against the stored hash."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Outbound payload after successful login/registration.

    user_id is included so the client can associate the token with
    the identity anchor used by the agent's thread_id.
    """
    access_token: str
    token_type: str = "bearer"
    user_id: str


class UserPublic(BaseModel):
    """Safe outbound representation of a user — excludes password_hash.

    Never expose the hash to the client, even though it can't be reversed.
    Defense in depth: minimize the attack surface of every response.
    """
    user_id: str
    email: str
    display_name: str | None
