from config import settings
from repositories.base import (
    AnswersetMetadataRepository,
    AuditLogRepository,
    RoleRepository,
    TemplateSettingsRepository,
    TenantRepository,
    UserRepository,
    WorkgroupRepository,
    WorkgroupTemplateRepository,
    WorkgroupUserRepository,
    WorkitemRepository,
)


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


def get_workgroup_repository() -> WorkgroupRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonWorkgroupRepository
        return JsonWorkgroupRepository()
    else:
        from repositories.db_repo import DbWorkgroupRepository
        return DbWorkgroupRepository()


def get_template_settings_repository() -> TemplateSettingsRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonTemplateSettingsRepository
        return JsonTemplateSettingsRepository()
    else:
        from repositories.db_repo import DbTemplateSettingsRepository
        return DbTemplateSettingsRepository()


def get_workgroup_template_repository() -> WorkgroupTemplateRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonWorkgroupTemplateRepository
        return JsonWorkgroupTemplateRepository()
    else:
        from repositories.db_repo import DbWorkgroupTemplateRepository
        return DbWorkgroupTemplateRepository()


def get_workgroup_user_repository() -> WorkgroupUserRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonWorkgroupUserRepository
        return JsonWorkgroupUserRepository()
    else:
        from repositories.db_repo import DbWorkgroupUserRepository
        return DbWorkgroupUserRepository()


def get_workitem_repository() -> WorkitemRepository:
    if settings.STORAGE_BACKEND == "json":
        from repositories.json_repo import JsonWorkitemRepository
        return JsonWorkitemRepository()
    else:
        from repositories.db_repo import DbWorkitemRepository
        return DbWorkitemRepository()


def get_answerset_metadata_repository() -> AnswersetMetadataRepository:
    # TODO: implement DbAnswersetMetadataRepository when DB migration is added
    from repositories.json_repo import JsonAnswersetMetadataRepository
    return JsonAnswersetMetadataRepository()


def get_audit_log_repository() -> AuditLogRepository:
    # TODO: implement DbAuditLogRepository when DB migration is added
    from repositories.json_repo import JsonAuditLogRepository
    return JsonAuditLogRepository()
