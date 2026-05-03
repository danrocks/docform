from fastapi import Request, HTTPException, Depends
from repositories.factory import get_tenant_repository
from auth_utils import get_current_user

RESERVED_SLUGS = {"admin", "www", "api"}


def get_current_tenant(request: Request):
    """Extract tenant from subdomain.

    Returns:
        - A tenant dict if on a tenant subdomain (e.g. girlguides.localhost)
        - None if on the 'admin' subdomain (superadmin context)
        - None if on bare domain (marketing/public page)
    """
    host = request.headers.get("host", "").split(":")[0]
    parts = host.split(".")

    if len(parts) >= 2 and parts[0] not in ("localhost", "docform"):
        slug = parts[0]
        if slug == "admin":
            return None
        if slug in RESERVED_SLUGS:
            raise HTTPException(status_code=404, detail="Not found")
        tenant = get_tenant_repository().get_by_slug(slug)
        if not tenant:
            raise HTTPException(status_code=404, detail="Organisation not found")
        if tenant.get("active") != "true":
            raise HTTPException(status_code=404, detail="Organisation not found")
        return tenant
    return None


def is_admin_subdomain(request: Request) -> bool:
    host = request.headers.get("host", "").split(":")[0]
    parts = host.split(".")
    print(f"Checking admin subdomain for host '{host}' - parts: {parts}")
    return len(parts) >= 2 and parts[0] == "admin"


def is_tenant_subdomain(request: Request) -> bool:
    host = request.headers.get("host", "").split(":")[0]
    parts = host.split(".")
    if len(parts) >= 2 and parts[0] not in ("localhost", "docform", "www", "api", "admin"):
        return True
    return False


def verify_tenant_match(request: Request, current_user: dict = Depends(get_current_user)):
    """Ensure the JWT's tenant_id matches the subdomain's tenant."""
    tenant = get_current_tenant(request)
    token_tenant_id = current_user.get("tenant_id")

    if is_admin_subdomain(request):
        if token_tenant_id is not None:
            raise HTTPException(status_code=401, detail="Not authorised for this context")
    elif is_tenant_subdomain(request):
        if tenant is None:
            raise HTTPException(status_code=404, detail="Organisation not found")
        if token_tenant_id != tenant["id"]:
            raise HTTPException(status_code=401, detail="Token not valid for this organisation")

    return current_user
