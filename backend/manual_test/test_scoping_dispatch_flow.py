import asyncio

from app.services.scoping_agent.scoping_agent import scoping_agent
from app.services.query_dispatcher import (
    QueryDispatcher,
)


async def run_flow(user_input: str):
    agent = await scoping_agent()

    scoping_result = await agent.ainvoke({"messages": [user_input]})

    print("\n=== SCOPING RESULT ===")
    print(scoping_result)

    dispatcher = QueryDispatcher()
    dispatch_result = await dispatcher.dispatch(scoping_result)

    print("\n=== DISPATCH RESULT ===")
    print(dispatch_result)

    return dispatch_result


if __name__ == "__main__":
    asyncio.run(run_flow("What is UNEP?"))

# python -m manual_test.test_scoping_dispatch_flow
