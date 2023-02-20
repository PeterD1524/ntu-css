import string
import urllib.parse
from collections.abc import Iterable

import lxml.html

import ntu_css.http


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


def document_from_string(html: str | bytes):
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


def check_response_url(
    response: ntu_css.http.Response,
    http_client: ntu_css.http.Client,
    path: str,
    query_keys: set[str],
):
    parse_result = urllib.parse.urlparse(response.url())
    assert parse_result.scheme == "https"
    assert parse_result.netloc == urllib.parse.urlparse(http_client.base_url()).netloc
    assert parse_result.path == path
    query = urllib.parse.parse_qs(
        parse_result.query, keep_blank_values=True, strict_parsing=True
    )
    assert query.keys() == query_keys
    assert all(len(values) == 1 for values in query.values())
    assert parse_result.params == ""
    assert parse_result.fragment == ""
    return query


def check_table_headers(
    table_row: lxml.html.HtmlElement, path: str, text_contents: Iterable[str]
):
    elements = assert_list_of_html_element(table_row.xpath(path))
    assert all(
        s == text_content(element)
        for (s, element) in zip(text_contents, elements, strict=True)
    )
    table_data_cells = assert_list_of_html_element(table_row.xpath("td"))
    assert not table_data_cells


def check_table_row_for_data(
    table_row: lxml.html.HtmlElement, table_header_text_contents: tuple[str, ...]
):
    table_headers = assert_list_of_html_element(table_row.xpath("th"))
    assert not table_headers
    table_data_cells = assert_list_of_html_element(table_row.xpath("td"))
    assert len(table_data_cells) == len(table_header_text_contents)
    return table_data_cells


def check_serial_number(serial_number: str):
    if len(serial_number) != 5:
        raise ValueError("serial number length should be 5")
    if not all(c in string.digits for c in serial_number):
        raise ValueError("serial number should all be digits")
