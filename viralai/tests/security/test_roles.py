from viralai.security.roles import Role


def test_role_ordering():
    assert Role.VIEWER < Role.RESEARCHER < Role.ADMIN


def test_role_equality():
    assert Role.ADMIN == Role.ADMIN
    assert Role.ADMIN != Role.VIEWER


def test_role_names():
    assert Role.VIEWER.name == "VIEWER"
    assert Role.RESEARCHER.name == "RESEARCHER"
    assert Role.ADMIN.name == "ADMIN"
