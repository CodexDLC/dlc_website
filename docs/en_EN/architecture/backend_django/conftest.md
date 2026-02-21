# 📜 Pytest Configuration (`conftest.py`)

[⬅️ Back](./README.md) | [🏠 Docs Root](../../../README.md)

This `conftest.py` file serves as the Pytest configuration file for the Django backend. It allows for the definition of fixtures, hooks, and other configurations that are automatically discovered and applied to tests within the project.

## Purpose

The primary purpose of `conftest.py` is to centralize test-specific configurations, making it easier to manage test environments and reduce boilerplate code in individual test files.

## `enable_db_access_for_all_tests` Fixture

```python
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.
    This prevents the need to mark every test with @pytest.mark.django_db.
    """
    pass
```

### Description

This fixture automatically enables database access for all tests that require it. By marking it with `autouse=True`, it eliminates the need to explicitly decorate every database-dependent test function with `@pytest.mark.django_db`.

### How it Works

*   `@pytest.fixture(autouse=True)`:
    *   `@pytest.fixture`: Decorator that marks `enable_db_access_for_all_tests` as a Pytest fixture.
    *   `autouse=True`: Instructs Pytest to automatically use this fixture for all tests in its scope without needing to explicitly request it.
*   `db`:
    This is a built-in fixture provided by `pytest-django` that sets up a transactional database for each test, ensuring that tests run in isolation and database changes are rolled back afterward. By including `db` as an argument, this fixture implicitly depends on `pytest-django`'s database setup.
*   `pass`:
    The body of the fixture is empty (`pass`) because its primary function is to trigger the `db` fixture and ensure its setup/teardown logic is executed for each test.

## Usage

With this `conftest.py` in place, any test function in the Django backend can interact with the database without needing explicit `@pytest.mark.django_db` decorators. For example:

```python
def test_my_model_creation():
    from myapp.models import MyModel
    MyModel.objects.create(name="Test")
    assert MyModel.objects.count() == 1
```
This test will automatically have database access.
