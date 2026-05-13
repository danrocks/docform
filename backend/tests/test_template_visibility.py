"""Tests for workgroup-based template visibility and submission access helpers."""
import pytest

from repositories.factory import (
    get_template_settings_repository,
    get_workgroup_repository,
    get_workgroup_template_repository,
    get_workgroup_user_repository,
)


@pytest.fixture
def make_user(user_repo):
    from auth_utils import hash_password

    def _make(user_id, role="staff", tenant_id="tenant-a"):
        return user_repo.create({
            "id": user_id,
            "username": user_id,
            "password": hash_password("pass1234"),
            "role": role,
            "name": user_id,
            "tenant_id": tenant_id,
        })

    return _make


@pytest.fixture
def make_workgroup(tenant_a):
    repo = get_workgroup_repository()

    def _make(name, requires_approval=False, tenant_id="tenant-a"):
        wg = {
            "id": f"wg-{name}",
            "name": name,
            "description": "",
            "tenant_id": tenant_id,
            "requires_approval": requires_approval,
            "created_at": "2026-05-13T00:00:00+00:00",
            "created_by": "admin",
        }
        return repo.create(wg)

    return _make


@pytest.fixture
def make_template_settings(tenant_a):
    repo = get_template_settings_repository()

    def _make(template_id, restricted=False, tenant_id="tenant-a"):
        return repo.create({
            "template_id": template_id,
            "tenant_id": tenant_id,
            "restricted_to_workgroups": restricted,
            "created_at": "2026-05-13T00:00:00+00:00",
            "created_by": "admin",
        })

    return _make


class TestTemplateVisibility:
    def test_template_without_settings_is_visible_to_all(self, seeded_roles, make_user):
        from routes.templates import _filter_templates_by_workgroup
        staff = make_user("staff-vis-1")
        result = _filter_templates_by_workgroup([{"id": "tpl-1"}], staff)
        assert [t["id"] for t in result] == ["tpl-1"]

    def test_unrestricted_settings_visible_to_all(
        self, seeded_roles, make_user, make_template_settings
    ):
        from routes.templates import _filter_templates_by_workgroup
        make_template_settings("tpl-2", restricted=False)
        staff = make_user("staff-vis-2")
        result = _filter_templates_by_workgroup([{"id": "tpl-2"}], staff)
        assert [t["id"] for t in result] == ["tpl-2"]

    def test_restricted_template_hidden_from_non_member(
        self, seeded_roles, make_user, make_template_settings
    ):
        from routes.templates import _filter_templates_by_workgroup
        make_template_settings("tpl-3", restricted=True)
        staff = make_user("staff-vis-3")
        result = _filter_templates_by_workgroup([{"id": "tpl-3"}], staff)
        assert result == []

    def test_restricted_template_visible_to_workgroup_member(
        self,
        seeded_roles,
        make_user,
        make_workgroup,
        make_template_settings,
    ):
        from routes.templates import _filter_templates_by_workgroup
        wg = make_workgroup("g1")
        make_template_settings("tpl-4", restricted=True)
        get_workgroup_template_repository().add_template(wg["id"], "tpl-4")
        staff = make_user("staff-vis-4")
        get_workgroup_user_repository().add_user(wg["id"], staff["id"])

        result = _filter_templates_by_workgroup([{"id": "tpl-4"}], staff)
        assert [t["id"] for t in result] == ["tpl-4"]

    def test_admin_sees_all_templates(
        self, seeded_roles, make_user, make_template_settings
    ):
        from routes.templates import _filter_templates_by_workgroup
        make_template_settings("tpl-5", restricted=True)
        admin = make_user("admin-vis", role="admin")
        result = _filter_templates_by_workgroup([{"id": "tpl-5"}], admin)
        assert [t["id"] for t in result] == ["tpl-5"]


class TestUserTemplateAccessHelper:
    def test_admin_always_has_access(self, seeded_roles, make_user, make_template_settings):
        from routes.submissions import _user_has_template_access
        make_template_settings("tpl-a", restricted=True)
        admin = make_user("admin-a", role="admin")
        assert _user_has_template_access("tpl-a", admin, "tenant-a") is True

    def test_staff_blocked_without_workgroup(
        self, seeded_roles, make_user, make_template_settings
    ):
        from routes.submissions import _user_has_template_access
        make_template_settings("tpl-b", restricted=True)
        staff = make_user("staff-b")
        assert _user_has_template_access("tpl-b", staff, "tenant-a") is False

    def test_staff_allowed_when_workgroup_includes_template(
        self,
        seeded_roles,
        make_user,
        make_workgroup,
        make_template_settings,
    ):
        from routes.submissions import _user_has_template_access
        wg = make_workgroup("g2")
        make_template_settings("tpl-c", restricted=True)
        get_workgroup_template_repository().add_template(wg["id"], "tpl-c")
        staff = make_user("staff-c")
        get_workgroup_user_repository().add_user(wg["id"], staff["id"])
        assert _user_has_template_access("tpl-c", staff, "tenant-a") is True

    def test_staff_allowed_when_template_unrestricted(
        self,
        seeded_roles,
        make_user,
        make_template_settings,
    ):
        from routes.submissions import _user_has_template_access
        make_template_settings("tpl-d", restricted=False)
        staff = make_user("staff-d")
        assert _user_has_template_access("tpl-d", staff, "tenant-a") is True


class TestSubmissionWorkgroupHelpers:
    def test_find_submission_path_locates_workgroup_subdir(
        self, tmp_path, monkeypatch, seeded_roles, make_workgroup, make_user
    ):
        """`_find_submission_path` should locate submissions stored under
        ``workgroups/<wid>/`` in addition to the root directory."""
        import json

        from routes import submissions as subs

        base = tmp_path / "submissions"
        wg = make_workgroup("g3")
        wg_dir = base / "workgroups" / wg["id"]
        wg_dir.mkdir(parents=True)
        (base / "root-sub.json").write_text(json.dumps({"id": "root-sub"}))
        (wg_dir / "wg-sub.json").write_text(
            json.dumps({"id": "wg-sub", "workgroup_id": wg["id"]})
        )

        monkeypatch.setattr(subs, "get_submissions_dir", lambda request: base)

        path, found_wg = subs._find_submission_path(None, "root-sub")
        assert path.name == "root-sub.json"
        assert found_wg is None

        path, found_wg = subs._find_submission_path(None, "wg-sub")
        assert path.parent == wg_dir
        assert found_wg == wg["id"]

        with pytest.raises(Exception):
            subs._find_submission_path(None, "missing")

    def test_read_submissions_with_workgroup_filter(self, tmp_path):
        import json

        from routes.submissions import read_submissions

        wg_dir = tmp_path / "workgroups" / "wg-r1"
        wg_dir.mkdir(parents=True)
        (wg_dir / "a.json").write_text(
            json.dumps({
                "id": "a",
                "template_id": "t1",
                "submitted_by": "u1",
                "submitted_at": "2026-05-13T00:00:00",
            })
        )

        items = read_submissions(tmp_path, workgroup_id="wg-r1")
        assert [i["id"] for i in items] == ["a"]

        items = read_submissions(tmp_path, workgroup_id="wg-missing")
        assert items == []


class TestSubmissionDirectories:
    def test_get_submissions_dir_with_workgroup(self, tmp_path, monkeypatch):
        from routes import submissions as subs

        monkeypatch.setattr(
            subs, "get_tenant_data_dir", lambda request, *parts: tmp_path
        )
        path = subs.get_submissions_dir(None, workgroup_id="wg-x")
        assert path == tmp_path / "workgroups" / "wg-x"
        assert path.exists()

    def test_get_generated_dir_with_workgroup(self, tmp_path, monkeypatch):
        from routes import submissions as subs

        monkeypatch.setattr(
            subs, "get_tenant_data_dir", lambda request, *parts: tmp_path
        )
        path = subs.get_generated_dir(None, workgroup_id="wg-y")
        assert path == tmp_path / "workgroups" / "wg-y"
        assert path.exists()
