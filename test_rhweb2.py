import pytest
from bs4 import BeautifulSoup as BS

MAGIC = "I6w4vAfFzvXV7S936ZNkRFQqer99WwjiTozu1xY6"

@pytest.mark.parametrize("purge", [False, True, False, True])
def test_index(client, purge):
    index = client.get("/" + ("?purge" if purge else ""))
    assert index.status_code == 200
    bs = BS(index.data, "lxml")
    title = bs.find("title")
    assert "RetroHerna" in title.string

def test_robots_txt(client):
    robots_txt = client.get("/robots.txt")
    assert robots_txt.status_code == 200
    assert b"Allow: /" in robots_txt.data

@pytest.mark.parametrize("log_in,magic,code,url", [
        (False, False, 200, "/"),
        (False, False, 200, "/login"), 
        (False, False, 200, "/active"),
        (False, False, 200, "/1-novinky"),
        (False, False, 200, "/1-novinky/1-prvni-tema-na-foru"),
        (False, False, 404, "/404"),
        (False, False, 403, "/7-burza"),
        (True,  False, 200, "/7-burza"),
        (True,  True,  200, "/8-pytest/22-edit-test-thread"),
        (True,  True,  200, "/8-pytest/22-edit-test-thread/edit/130"),
        (True,  False, 200, "/edit-forum/8"),
        (True,  False, 200, "/edit-category/4"),
        (True,  False, 200, "/users/1-admin"),
        (True,  False, 200, "/users/1-admin/edit"),
        (True,  False, 200, "/users/1-admin/threads"),
        (True,  False, 200, "/users/"),
        (True,  False, 200, "/groups/"),
        (True,  False, 200, "/groups/1/edit"),
        
    ])
def test_forum_page(client, url, code, log_in, magic):
    if log_in:
        login(client)
    
    page = client.get("/forum"+url)
    assert page.status_code == code
    if code == 200:
        bs = BS(page.data, "lxml")
        title = bs.find("title")
        assert "RetroHerna" in title.string
    if magic:
        assert MAGIC in str(page.data)
  
def login(client, user="admin", password="test"):
    page = client.post("/forum/login", data=dict(name=user, password=password))
    return page

@pytest.mark.parametrize("user,password,valid", [
    ("random_invalid_user_name_f2iro54ejf7oie", "jkdslfjkdlasf", False),
    ("admin", "test", True)
])
def test_forum_login(client, user, password, valid):
    page = login(client, user, password)
    if not valid:
        assert page.status_code == 200
    else:
        assert page.status_code == 302

