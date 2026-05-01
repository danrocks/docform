from config import settings
from repositories.base import RoleRepository, TenantRepository, UserRepository


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


def get_tenant_repository() -> TenantRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonTenantRepository
        return JsonTenantRepository()
    else:
        from repositories.db_repo import DbTenantRepository
        return DbTenantRepository()
