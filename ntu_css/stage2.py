import dataclasses
from collections.abc import Iterable

import lxml.html

import ntu_css.exceptions
import ntu_css.http
import ntu_css.single_sign_on
import ntu_css.something
import ntu_css.utils


class ErrorMessageInContentDivisionFromServer(ntu_css.exceptions.Error):
    pass


def table_row_to_course_selection_list_item(table_row: lxml.html.HtmlElement):
    table_data_cells = ntu_css.utils.assert_list_of_html_element(table_row.xpath("td"))
    assert len(table_data_cells) == 9

    priority = int(
        ntu_css.utils.remove_suffix(
            ntu_css.utils.assert_str(
                ntu_css.utils.xpath_only_one_html_element(
                    table_data_cells[7], "font"
                ).text
            ),
            "\xa0\xa0 (",
        )
    )

    def font_text_content(element: lxml.html.HtmlElement):
        return ntu_css.utils.text_content(
            ntu_css.utils.xpath_only_one_html_element(element, "font")
        )

    return CourseSelectionListItem(
        serial_number=font_text_content(table_data_cells[0]),
        curriculum_number=font_text_content(table_data_cells[1]),
        class_=font_text_content(table_data_cells[2]),
        curriculum_name=font_text_content(table_data_cells[3]).rstrip(" "),
        credits=font_text_content(table_data_cells[4]),
        instructor=ntu_css.utils.remove_suffix(
            font_text_content(table_data_cells[5]), "    "
        ),
        course_schedule=ntu_css.utils.remove_suffix(
            ntu_css.utils.remove_prefix(font_text_content(table_data_cells[6]), " "),
            " ",
        ),
        priority=priority,
        remark=ntu_css.utils.remove_suffix(
            ntu_css.utils.text_content(table_data_cells[8]), "\xa0"
        ),
    )


@dataclasses.dataclass
class CourseSelectionListItem:
    serial_number: str
    curriculum_number: str
    class_: str
    curriculum_name: str
    credits: str
    instructor: str
    course_schedule: str
    priority: int
    remark: str


def check_priority(priority: int):
    if priority not in range(1, 100):
        raise ValueError("priority should be in range(1, 100)")


@dataclasses.dataclass
class CourseSelectionClient:
    session_info: ntu_css.something.SessionInfo

    client: ntu_css.http.Client

    async def list_courses(self):
        response = await self.client.request(
            "GET",
            "/coursetake/index.php/ctake/mainscr",
            params=(
                ("regno", self.session_info.regno),
                ("extid", self.session_info.extid),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        table_rows = ntu_css.utils.assert_list_of_html_element(
            document.xpath("/html/body/div/table/tr")
        )
        assert len(table_rows) >= 1
        table_headers = ntu_css.utils.assert_list_of_html_element(
            table_rows[0].xpath("th")
        )
        assert len(table_headers) == 9
        table_data_cells = ntu_css.utils.assert_list_of_html_element(
            table_rows[0].xpath("td")
        )
        assert not table_data_cells
        for table_row in table_rows[1:]:
            yield table_row_to_course_selection_list_item(table_row)

    async def add_course(self, serno: str, priority: int):
        ntu_css.utils.check_serial_number(serno)
        check_priority(priority)
        response = await self.client.request(
            "GET",
            "/coursetake/index.php/ctake/add-cou",
            params=(
                ("serno", serno),
                ("cougrp", ""),
                ("regno", self.session_info.regno),
                ("extid", self.session_info.extid),
                ("code", "2"),
                ("sure", "確定登記"),
                ("priority", str(priority)),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        content_divisions = ntu_css.utils.assert_list_of_html_element(
            document.xpath('//*[@id="card1"]/div/table/tr/td/div')
        )
        if len(content_divisions) == 1:
            text_content = ntu_css.utils.text_content(content_divisions[0])
            if text_content != "\n\t\t\t\t\t加選登記成功\t\t\t\t":
                raise ErrorMessageInContentDivisionFromServer(repr(text_content))
            return
        assert not content_divisions
        content_division = ntu_css.utils.xpath_only_one_html_element(
            document, "/html/body/div/div"
        )
        text_content = ntu_css.utils.text_content(content_division)
        raise ErrorMessageInContentDivisionFromServer(repr(text_content))

    async def delete_course(self, serno: str):
        response = await self.client.request(
            "GET",
            "/coursetake/index.php/ctake/del-cou",
            params=(
                ("serno", serno),
                ("regno", self.session_info.regno),
                ("extid", self.session_info.extid),
                ("sure", "確定退選"),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        content_division = ntu_css.utils.xpath_only_one_html_element(
            document, '//*[@id="card1"]/div/div'
        )
        text_content = ntu_css.utils.text_content(content_division)
        if (
            not text_content
            == f"\n\t\t\t\t\t\t\t\t\t退選科目流水號: {serno}完成退選\t\t\t\t\t\t\t\t"
        ):
            raise ErrorMessageInContentDivisionFromServer(repr(text_content))


@dataclasses.dataclass
class LoginClient:
    client: ntu_css.http.Client

    async def login(self, username: str, password: str):
        response = await self.client.request(
            "GET", "/coursetake/login.aspx", follow_redirects=True
        )
        request = ntu_css.single_sign_on.login(
            response=response, username=username, password=password
        )
        response = await self.client.request(
            request.method, request.url, data=request.data, follow_redirects=True
        )
        response.raise_for_status()
        query = ntu_css.utils.check_response_url(
            response=response,
            http_client=self.client,
            path="/coursetake/index.php/survey-note",
            query_keys={"regno", "lang", "extid"},
        )
        return ntu_css.something.SessionInfo(
            regno=query["regno"][0], lang=query["lang"][0], extid=query["extid"][0]
        )


def check_course_selection(items: Iterable[CourseSelectionListItem]):
    serial_numbers = set[str]()
    priorities = set[int]()
    for item in items:
        ntu_css.utils.check_serial_number(item.serial_number)
        if item.serial_number in serial_numbers:
            raise ValueError("duplicate serial numbers found")
        serial_numbers.add(item.serial_number)
        check_priority(item.priority)
        if item.priority in priorities:
            raise ValueError("duplicate priorities found")
        priorities.add(item.priority)
