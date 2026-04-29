from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, ForeignKey("roles.name"), nullable=False)
    name = Column(String, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "role": self.role,
            "name": self.name,
        }


class Role(Base):
    __tablename__ = "roles"

    name = Column(String, primary_key=True)
    description = Column(String, nullable=False, default="")

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}
