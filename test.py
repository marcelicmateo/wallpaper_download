#!/usr/bin/python
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import react
from requests_threads import AsyncSession

session = AsyncSession(n=4)


@inlineCallbacks
def main(reactor):
    responses = []
    for i in range(100):
        print(i)
        responses.append(session.get("http://httpbin.org/get"))

    for response in responses:
        r = yield response
        print(r)


if __name__ == "__main__":
    react(main)
