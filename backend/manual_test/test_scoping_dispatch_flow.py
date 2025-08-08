import asyncio

from app.services.scoping_agent.scoping_agent import scoping_agent
from app.services.query_dispatcher import (
    QueryDispatcher,
)
from app.services.response_generator import (
    generate_response_from_context,
)
from app.db.session import SessionLocal


async def run_flow(user_input: str):
    db = SessionLocal()

    agent = await scoping_agent()

    scoping_result = await agent.ainvoke({"messages": [user_input]})

    print("\n=== SCOPING RESULT ===")
    print(scoping_result)

    dispatcher = QueryDispatcher()
    dispatch_result = await dispatcher.dispatch(scoping_result)

    # print("\n=== DISPATCH RESULT ===")
    # print(dispatch_result)

    async for chunk in generate_response_from_context(
        query=user_input,
        tool_contexts=[dispatch_result["processed_result"]],
        db=db,
    ):
        print(chunk, "123")

    return dispatch_result


if __name__ == "__main__":
    asyncio.run(run_flow("What do you know about UNEP programm?"))
    # asyncio.run(run_flow("Find an image about cashew gumosis."))

# python -m manual_test.test_scoping_dispatch_flow
