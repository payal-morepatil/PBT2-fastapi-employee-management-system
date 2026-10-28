import asyncio
import time
from fastapi import  APIRouter
router = APIRouter(prefix="/week6", tags=["week6"])
async  def get_attendance():
    await asyncio.sleep(2)

    return {
        'attendance':'present'
    }
async def get_leave_summary():
    await asyncio.sleep(2)

    return {
        'leaves': 8
    }
@router.get("/async-demo")
async def async_demo():
    start = time.perf_counter()

    attendance, leave = await asyncio.gather(
        get_attendance(),
        get_leave_summary()
    )
    elapsed = round(time.perf_counter() - start,2)
    return {
        'message':'async tasks completed',
        'attendance': attendance,
        'leave summary': leave,
        'elapsed_seconds': elapsed
    }
@router.get("/sequential-demo")
async def sequential_demo():
    start= time.perf_counter()
    attendance =await get_attendance()
    leave = await get_leave_summary()
    elapsed = round(time.perf_counter() - start,2)
    return {
        'message':' tasks completed',
        'attendance': attendance,
        'leave summary': leave,
        'elapsed_seconds': elapsed
    }