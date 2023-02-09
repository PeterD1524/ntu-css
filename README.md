# ntu-css
![](https://if192.aca.ntu.edu.tw/index_inc/head.jpg)
## 初選二階 Example
```python
import asyncio

import httpx

import ntu_css.http
import ntu_css.something
import ntu_css.stage2


async def main():
    client = ntu_css.http.HttpxClient(
        httpx.AsyncClient(base_url=ntu_css.something.BASE_URLS[1])
    )

    login_client = ntu_css.stage2.LoginClient(client)

    session_info = await login_client.login(username=USERNAME, password=PASSWORD)

    course_selection_client = ntu_css.stage2.CourseSelectionClient(session_info, client)

    # 加選
    await course_selection_client.add_course("97001", 1)

    # 退選
    await course_selection_client.delete_course("97001")

    # 選課紀錄
    async for course_selection_list_item in course_selection_client.list_courses():
        print(course_selection_list_item)

    # check if 選課紀錄 makes sense
    course_selection_list_items = [
        item async for item in course_selection_client.list_courses()
    ]
    ntu_css.stage2.check_course_selection(course_selection_list_items)
```
