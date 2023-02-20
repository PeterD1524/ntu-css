import dataclasses
import enum
from collections.abc import Iterable

import lxml.html

import ntu_css.exceptions
import ntu_css.http
import ntu_css.single_sign_on
import ntu_css.utils

RESULT_TABLE_HEADER_TEXT_CONTENTS = (
    "流水號",
    "課號",
    "課程識別碼",
    "班次",
    "課程名稱",
    "學分",
    "教師姓名",
    "備註",
)

OPERATION_LOG_TABLE_HEADER_TEXT_CONTENTS = ("時間", "訊息")

FAILED_COURSES_TABLE_HEADER_TEXT_CONTENTS = (
    "流水號",
    "課號",
    "課程識別碼",
    "班次",
    "課程名稱",
    "學分",
    "教師姓名",
    "未分發上原因",
)


def check_table_headers(table_row: lxml.html.HtmlElement, text_contents: Iterable[str]):
    ntu_css.utils.check_table_headers(table_row, "th/strong", text_contents)


@dataclasses.dataclass
class ResultItem:
    serial_number: str
    curriculum_number: str
    curriculum_identity_number: str
    class_: str
    course_name: str
    credits: str
    instructor: str
    mark: str


def table_row_to_result_item(table_row: lxml.html.HtmlElement):
    table_data_cells = ntu_css.utils.check_table_row_for_data(
        table_row, RESULT_TABLE_HEADER_TEXT_CONTENTS
    )
    return ResultItem(
        serial_number=ntu_css.utils.text_content(table_data_cells[0]),
        curriculum_number=ntu_css.utils.text_content(table_data_cells[1]),
        curriculum_identity_number=ntu_css.utils.text_content(table_data_cells[2]),
        class_=ntu_css.utils.text_content(table_data_cells[3]),
        course_name=ntu_css.utils.text_content(table_data_cells[4]).rstrip(" "),
        credits=ntu_css.utils.text_content(table_data_cells[5]),
        instructor=ntu_css.utils.text_content(table_data_cells[6]).rstrip(" "),
        mark=ntu_css.utils.text_content(table_data_cells[7]),
    )


@dataclasses.dataclass
class OperationLogItem:
    time: str
    message: str


def table_row_to_operation_log_item(table_row: lxml.html.HtmlElement):
    table_data_cells = ntu_css.utils.check_table_row_for_data(
        table_row, OPERATION_LOG_TABLE_HEADER_TEXT_CONTENTS
    )
    return OperationLogItem(
        time=ntu_css.utils.text_content(table_data_cells[0]),
        message=ntu_css.utils.text_content(table_data_cells[1]),
    )


@dataclasses.dataclass
class FailedCourse:
    serial_number: str
    curriculum_number: str
    curriculum_identity_number: str
    class_: str
    course_name: str
    credits: str
    instructor: str
    reason: str


def table_row_to_failed_course(table_row: lxml.html.HtmlElement):
    table_data_cells = ntu_css.utils.check_table_row_for_data(
        table_row, FAILED_COURSES_TABLE_HEADER_TEXT_CONTENTS
    )
    return FailedCourse(
        serial_number=ntu_css.utils.text_content(table_data_cells[0]),
        curriculum_number=ntu_css.utils.text_content(table_data_cells[1]),
        curriculum_identity_number=ntu_css.utils.text_content(table_data_cells[2]),
        class_=ntu_css.utils.text_content(table_data_cells[3]),
        course_name=ntu_css.utils.text_content(table_data_cells[4]).rstrip(),
        credits=ntu_css.utils.text_content(table_data_cells[5]),
        instructor=ntu_css.utils.text_content(table_data_cells[6]).rstrip(),
        reason=ntu_css.utils.text_content(table_data_cells[7]).rstrip(),
    )


class ResultKind(enum.Enum):
    preregistration_stage1 = "1"
    preregistration_stage2 = "2"


@dataclasses.dataclass
class TableNotFound(ntu_css.exceptions.Error):
    heading_message: str

    def __str__(self):
        return repr(self.heading_message)


@dataclasses.dataclass
class Client:
    client: ntu_css.http.Client

    async def login(self, username: str, password: str):
        response = await self.client.request(
            "GET",
            "https://if177.aca.ntu.edu.tw/qcaureg/stulogin.asp",
            follow_redirects=True,
        )

        request = ntu_css.single_sign_on.login(response, username, password)

        response = await self.client.request(
            request.method, request.url, data=request.data, follow_redirects=True
        )
        response.raise_for_status()
        assert response.url() == "https://if177.aca.ntu.edu.tw/qcaureg/index.asp"

    async def get_result(self, kind: ResultKind):
        response = await self.client.request(
            "GET",
            "https://if177.aca.ntu.edu.tw/qcaureg/index.asp",
            params=(("kind", ntu_css.utils.assert_str(kind.value)),),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.content())
        table_rows = ntu_css.utils.assert_list_of_html_element(
            document.xpath('//*[@id="content"]/center[1]/table/tr')
        )
        assert len(table_rows) >= 1
        check_table_headers(table_rows[0], RESULT_TABLE_HEADER_TEXT_CONTENTS)
        for table_row in table_rows[1:]:
            yield table_row_to_result_item(table_row)

    async def get_operation_log(self, kind: ResultKind):
        response = await self.client.request(
            "GET",
            "https://if177.aca.ntu.edu.tw/qcaureg/displayLog.asp",
            params=(("kind", ntu_css.utils.assert_str(kind.value)),),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.content())
        table_rows = ntu_css.utils.assert_list_of_html_element(
            document.xpath('//*[@id="content"]/center/table/tr')
        )
        if not table_rows:
            heading = ntu_css.utils.xpath_only_one_html_element(
                document, '//*[@id="content"]/center/h2'
            )
            text_content = ntu_css.utils.text_content(heading)
            raise TableNotFound(heading_message=text_content)
        check_table_headers(table_rows[0], OPERATION_LOG_TABLE_HEADER_TEXT_CONTENTS)
        for table_row in table_rows[1:]:
            yield table_row_to_operation_log_item(table_row)

    async def get_failed_courses(self, kind: ResultKind):
        response = await self.client.request(
            "GET",
            "https://if177.aca.ntu.edu.tw/qcaureg/DistFailCourses.asp",
            params=(("kind", ntu_css.utils.assert_str(kind.value)),),
        )
        response.raise_for_status()
        document = ntu_css.utils.document_from_string(response.content())
        table_rows = ntu_css.utils.assert_list_of_html_element(
            document.xpath('//*[@id="content"]/table/tr')
        )
        assert len(table_rows) >= 1
        check_table_headers(table_rows[0], FAILED_COURSES_TABLE_HEADER_TEXT_CONTENTS)
        for table_row in table_rows[1:]:
            yield table_row_to_failed_course(table_row)
