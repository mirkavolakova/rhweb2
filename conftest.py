import pytest
#from rhweb2 import app

@pytest.fixture
def app():
    from rhweb2 import app
    return app

