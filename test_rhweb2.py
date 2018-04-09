import pytest
from bs4 import BeautifulSoup as BS

@pytest.mark.parametrize("purge", [False, True, False, True])
def test_index(client, purge):
    index = client.get("/" + ("?purge" if purge else ""))
    assert index.status_code == 200
    bs = BS(index.data, "lxml")
    title = bs.find("title")
    assert "RetroHerna" in title.string

@pytest.mark.parametrize("url,code", [
        ("/", 200),
        ("/login", 200), 
        ("/1-novinky", 200),
        ("/1-novinky/1-prvni-tema-na-foru", 200),
        ("/7-burza", 403),
        ("/404", 404),
    ])
def test_forum_page(client, url, code):
    page = client.get("/forum"+url)
    assert page.status_code == code
    if code == 200:
        bs = BS(page.data, "lxml")
        title = bs.find("title")
        assert "RetroHerna" in title.string
    
