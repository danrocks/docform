from config import settings
from repositories.base import RoleRepository, UserRepository


def get_user_repository() -> UserRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonUserRepository
        return JsonUserRepository()
    else:
        from repositories.db_repo import DbUserRepository
        return DbUserRepository()


def get_role_repository() -> RoleRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonRoleRepository
        return JsonRoleRepository()
    else:
        from repositories.db_repo import DbRoleRepository
        return DbRoleRepository()
