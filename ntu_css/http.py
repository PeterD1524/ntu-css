import abc
import dataclasses
from typing import Any

import httpx


@dataclasses.dataclass
class Request:
    method: str
    url: str
    data: Any


class Response(abc.ABC):
    @abc.abstractmethod
    def raise_for_status(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def text(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def url(self) -> str:
        raise NotImplementedError


class Client(abc.ABC):
    @abc.abstractmethod
    def base_url(self) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        *,
        data=None,
        params=None,
        follow_redirects: bool = False,
    ) -> Response:
        raise NotImplementedError


@dataclasses.dataclass
class HttpxResponse(Response):
    response: httpx.Response

    def raise_for_status(self):
        self.response.raise_for_status()

    def text(self):
        return self.response.text

    def url(self):
        return str(self.response.url)


@dataclasses.dataclass
class HttpxClient(Client):
    client: httpx.AsyncClient

    def base_url(self):
        return str(self.client.base_url)

    async def request(
        self,
        method: str,
        url: str,
        *,
        data=None,
        params=None,
        follow_redirects: bool = False,
    ):
        return HttpxResponse(
            await self.client.request(
                method, url, data=data, params=params, follow_redirects=follow_redirects
            )
        )
