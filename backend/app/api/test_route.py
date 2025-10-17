from fastapi import APIRouter
from app.tasks.test_task import add
from app.celery_app import celery_app

router = APIRouter()

@router.get("/add")
def add_numbers(x: int, y: int):
    task = add.delay(x, y)
    return {"task_id": task.id}


@router.get("/task_status/{task_id}")
def get_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {"state": task.state, "result": task.result}
