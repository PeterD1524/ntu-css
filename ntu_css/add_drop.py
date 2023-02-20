import copy
import dataclasses
import re
import urllib.parse

import lxml.html

import ntu_css.http
import ntu_css.single_sign_on
import ntu_css.something
import ntu_css.utils

COURSE_SELECTION_LIST_TABLE_HEADER_TEXT_CONTENTS = {
    ntu_css.something.SESSION_INFO_LANG_CHINESE: (
        "狀態",
        "流水號",
        "課號/識別碼",
        "課程名稱",
        "班次",
        "學分",
        "授課老師",
        "上 課 時 間",
        "衝堂志願",
        "備註",
        "\xa0",
    ),
    ntu_css.something.SESSION_INFO_LANG_ENGLISH: (
        "Status",
        "Serial number",
        "Curriculum number",
        "Course name",
        "Course class",
        "Credits",
        "Instructor",
        "Course schedule",
        "Conflict Wish",
        "Remarks",
        "\xa0",
    ),
}


@dataclasses.dataclass
class CourseSelectionListItem:
    status: str
    serial_number: str
    curriculum_number: str
    curriculum_identity_number: str
    course_name: str
    course_class: str
    credits: str
    instructor: str
    course_schedule: str
    conflict_wish: str
    remarks: str


def table_row_to_course_selection_list_item(
    table_row: lxml.html.HtmlElement, table_header_text_contents: tuple[str, ...]
):
    table_data_cells = ntu_css.utils.check_table_row_for_data(
        table_row, table_header_text_contents
    )
    texts = [ntu_css.utils.assert_str(text) for text in table_data_cells[2].itertext()]
    assert len(texts) == 2
    return CourseSelectionListItem(
        status=ntu_css.utils.text_content(table_data_cells[0]),
        serial_number=ntu_css.utils.text_content(table_data_cells[1]),
        curriculum_number=ntu_css.utils.remove_suffix(texts[0], " "),
        curriculum_identity_number=ntu_css.utils.remove_prefix(texts[1], "\n\t    "),
        course_name=ntu_css.utils.text_content(table_data_cells[3]).rstrip(" "),
        course_class=ntu_css.utils.remove_suffix(
            ntu_css.utils.text_content(table_data_cells[4]), "\xa0"
        ),
        credits=ntu_css.utils.text_content(table_data_cells[5]),
        instructor=ntu_css.utils.text_content(table_data_cells[6]).rstrip(" "),
        course_schedule=ntu_css.utils.remove_suffix(
            ntu_css.utils.text_content(table_data_cells[7]), "\t\n  "
        ).removeprefix(" "),
        conflict_wish=ntu_css.utils.remove_suffix(
            ntu_css.utils.text_content(table_data_cells[8]), "\xa0"
        ),
        remarks=ntu_css.utils.remove_suffix(
            ntu_css.utils.text_content(table_data_cells[9]), "\xa0"
        ),
    )


@dataclasses.dataclass
class Type1Course:
    serial_number: str


def copy_session_info(session_info: ntu_css.something.SessionInfo | None):
    assert session_info is not None
    return copy.copy(session_info)


def check_text_content(document: lxml.html.HtmlElement, path: str, text_content: str):
    element = ntu_css.utils.xpath_only_one_html_element(document, path)
    assert ntu_css.utils.text_content(element) == text_content


@dataclasses.dataclass
class CourseSelectionClient:
    session_info: ntu_css.something.SessionInfo | None

    http_client: ntu_css.http.Client

    async def login(self, username: str, password: str):
        response = await self.http_client.request(
            "GET", "/coursetake2/login.aspx", follow_redirects=True
        )
        request = ntu_css.single_sign_on.login(
            response=response, username=username, password=password
        )
        response = await self.http_client.request(
            request.method, request.url, data=request.data, follow_redirects=True
        )
        response.raise_for_status()
        ntu_css.utils.check_response_url(
            response=response,
            http_client=self.http_client,
            path="/coursetake2/user/coursetake2",
            query_keys={"regno", "lang"},
        )
        m = re.fullmatch(
            r"""<script type="text/javascript">\r\nwindow\.location\.href = \'(/coursetake2/user/chk-sess\?sess=[0-9a-f]{32}[0-9A-Z]{9}[0-9]{12}&language=)\';\r\n</script>""",
            response.text(),
        )
        assert m is not None
        url = urllib.parse.urljoin(response.url(), ntu_css.utils.assert_str(m.group(1)))
        response = await self.http_client.request("GET", url, follow_redirects=True)
        response.raise_for_status()
        query = ntu_css.utils.check_response_url(
            response=response,
            http_client=self.http_client,
            path="/coursetake2/coutake/mainscr",
            query_keys={"regno", "lang", "extid"},
        )
        self.session_info = ntu_css.something.SessionInfo(
            regno=query["regno"][0], lang=query["lang"][0], extid=query["extid"][0]
        )

    async def list_courses(self):
        session_info = copy_session_info(self.session_info)
        table_header_text_contents = COURSE_SELECTION_LIST_TABLE_HEADER_TEXT_CONTENTS[
            session_info.lang
        ]
        response = await self.http_client.request(
            "GET",
            "/coursetake2/coutake/mainscr",
            params=(
                ("regno", session_info.regno),
                ("lang", session_info.lang),
                ("extid", session_info.extid),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        ntu_css.utils.check_table_headers(
            table_row=ntu_css.utils.xpath_only_one_html_element(
                document, '//*[@id="div-main"]/center/table/tr'
            ),
            path="th",
            text_contents=table_header_text_contents,
        )
        table_rows = ntu_css.utils.assert_list_of_html_element(
            document.xpath('//*[@id="div-main"]/center/table/tbody[1]/tr')
        )
        for table_row in table_rows:
            yield table_row_to_course_selection_list_item(
                table_row=table_row,
                table_header_text_contents=table_header_text_contents,
            )

    async def add_course(self, course: Type1Course):
        ntu_css.utils.check_serial_number(course.serial_number)
        session_info = copy_session_info(self.session_info)
        if session_info.lang == ntu_css.something.SESSION_INFO_LANG_CHINESE:
            sure = "確定選課"
            serial_number_text = "流水號："
        elif session_info.lang == ntu_css.something.SESSION_INFO_LANG_ENGLISH:
            sure = "Confirm registration"
            serial_number_text = "Serial number："
        else:
            assert False
        response = await self.http_client.request(
            "GET",
            "/coursetake2/coutake/add-cou",
            params=(
                ("serno", course.serial_number),
                ("cougrp", ""),
                ("opFld", "serno"),
                ("cou_no", ""),
                ("cou_cls", ""),
                ("couid_1", ""),
                ("couid_2", ""),
                ("couid_cls", ""),
                ("authno", ""),
                ("regno", session_info.regno),
                ("extid", session_info.extid),
                ("txtRank", ""),
                ("sure", sure),
                ("lang", session_info.lang),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        check_text_content(document, '//*[@id="div-main"]/h3/font', "加選成功")
        check_text_content(
            document,
            '//*[@id="div-main"]/table/tr[2]/td[1]/center/table/tr[1]/th/font',
            serial_number_text,
        )
        check_text_content(
            document,
            '//*[@id="div-main"]/table/tr[2]/td[1]/center/table/tr[1]/td/font',
            course.serial_number,
        )

    async def delete_course(self, serial_number: str):
        ntu_css.utils.check_serial_number(serial_number)
        session_info = copy_session_info(self.session_info)
        if session_info.lang == ntu_css.something.SESSION_INFO_LANG_CHINESE:
            sure = "確定退選"
            student_id_number_text = "學號： "
            serial_number_text = "退選科目流水號:"
            main_text = ["\r\n", " 完成退選", " ", "\n\n"]
        elif session_info.lang == ntu_css.something.SESSION_INFO_LANG_ENGLISH:
            sure = "Confirm de-registration"
            student_id_number_text = "Student ID number:  "
            serial_number_text = "Serial number of the de-registered course:"
            main_text = ["\r\n", " De-registration completed.", " ", "\n\n"]
        else:
            assert False
        response = await self.http_client.request(
            "GET",
            "/coursetake2/coutake/del-cou",
            params=(
                ("serno", serial_number),
                ("regno", session_info.regno),
                ("extid", session_info.extid),
                ("sure", sure),
                ("lang", session_info.lang),
            ),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.text())
        check_text_content(
            document, '//*[@id="div-main"]/table/tr[1]/td[1]', student_id_number_text
        )
        check_text_content(
            document, '//*[@id="div-main"]/table/tr[1]/td[2]', session_info.regno
        )
        check_text_content(
            document, '//*[@id="div-main"]/table/tr[2]/td[1]', serial_number_text
        )
        check_text_content(
            document, '//*[@id="div-main"]/table/tr[2]/td[2]', serial_number
        )
        assert document.xpath('//*[@id="div-main"]/text()') == main_text
