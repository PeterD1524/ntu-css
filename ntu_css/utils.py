import lxml.html


def assert_str(o):
    assert isinstance(o, str)
    return o


def assert_list(o):
    assert isinstance(o, list)
    return o


def assert_html_element(o):
    assert isinstance(o, lxml.html.HtmlElement)
    return o


def assert_form_element(o):
    assert isinstance(o, lxml.html.FormElement)
    return o


def assert_list_of_form_element(o):
    return [assert_form_element(o) for o in assert_list(o)]


def assert_list_of_html_element(o):
    return [assert_html_element(o) for o in assert_list(o)]


def document_from_string(html: str):
    return assert_html_element(lxml.html.document_fromstring(html))


def text_content(element: lxml.html.HtmlElement):
    return assert_str(element.text_content())


def xpath_only_one_html_element(element: lxml.html.HtmlElement, path: str):
    result = assert_list_of_html_element(element.xpath(path))
    assert len(result) == 1
    return result[0]


def remove_prefix(s: str, prefix: str):
    assert s.startswith(prefix)
    return s[len(prefix) :]


def remove_suffix(s: str, suffix: str):
    assert s.endswith(suffix)
    return s[: -len(suffix)]
