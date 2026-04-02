from pytest_archon import archrule

def test_api_does_not_import_db_models():
    (
        archrule("API layers must not directly import DB models")
        .match("app.api.*")
        .should_not_import("app.db.models")
        .check("app")
    )

def test_core_is_independent():
    (
        archrule("Core domain models must not depend on outer layers")
        .match("app.core.*")
        .should_not_import("app.api.*", "app.workers.*", "app.db.*", "app.repositories.*")
        .check("app")
    )

def test_db_models_are_independent():
    (
        archrule("DB models must not depend on outer layers")
        .match("app.db.models")
        .should_not_import("app.api.*", "app.services.*", "app.workers.*")
        .check("app")
    )

def test_repositories_must_not_import_higher_layers():
    (
        archrule("Repositories must not depend on services or API routers")
        .match("app.repositories.*")
        .should_not_import("app.api.*", "app.services.*")
        .check("app")
    )

def test_services_must_not_import_api():
    (
        archrule("Services must not depend on the API layer")
        .match("app.services.*")
        .should_not_import("app.api.*")
        .check("app")
    )
