import urllib.parse

import lxml.html

import ntu_css.http
import ntu_css.utils


def form_fields(form: lxml.html.FormElement):
    for key in form.fields:
        assert isinstance(key, str)
        value = form.fields[key]
        if value is None:
            value = None
        else:
            assert isinstance(value, str)
        yield (key, value)


def login(response: ntu_css.http.Response, username: str, password: str):
    response.raise_for_status()
    assert response.url() == "https://web2.cc.ntu.edu.tw/p/s/login2/p1.php"

    document = ntu_css.utils.document_from_string(response.text())
    (form,) = ntu_css.utils.assert_list_of_form_element(
        document.xpath('//*[@id="content"]/form[@name="p1"]')
    )
    data = dict(form_fields(form))
    assert "user" in data
    data["user"] = username
    assert "pass" in data
    data["pass"] = password
    action = ntu_css.utils.assert_str(form.action)
    method = ntu_css.utils.assert_str(form.method)
    assert method == "POST"
    data = {k: ntu_css.utils.assert_str(v) for k, v in data.items()}
    return ntu_css.http.Request(
        method=method, url=urllib.parse.urljoin(response.url(), action), data=data
    )
