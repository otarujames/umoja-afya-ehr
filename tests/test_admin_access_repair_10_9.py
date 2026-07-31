from backend.app.access_control import ROLE_TEMPLATES, FUNCTION_CATALOG, DEPARTMENT_CATALOG
from scripts.generate_preloaded_users import build_manifest


def test_admin_template_is_complete():
    admin = ROLE_TEMPLATES["admin"]
    assert set(admin["functions"]) == {x.code for x in FUNCTION_CATALOG}
    assert set(admin["departments"]) == {x.code for x in DEPARTMENT_CATALOG}


def test_platform_admin_manifest_has_all_countries():
    users = {x["username"]: x for x in build_manifest()["users"]}
    assert set(users["platform.admin"]["country_codes"]) == {"TZ", "KE", "NG"}
    assert users["platform.admin"]["all_facilities_in_countries"] is True


def test_country_admins_are_country_isolated_but_full_admin_role():
    users = {x["username"]: x for x in build_manifest()["users"]}
    for username, country in (("tz.admin", "TZ"), ("ke.admin", "KE"), ("ng.admin", "NG")):
        assert users[username]["role_code"] == "admin"
        assert users[username]["country_codes"] == [country]
        assert users[username]["all_facilities_in_countries"] is True
