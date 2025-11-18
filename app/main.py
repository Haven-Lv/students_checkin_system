from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from datetime import timedelta
import io
import qrcode # 确保已安装 qrcode[pil]
from datetime import datetime
from . import coord_utils
from . import db_utils
from .db_utils import get_db_connection
# 导入我们创建的模块
from . import models
from . import security

app = FastAPI(
    title="学生活动签到系统",
    description="API for student check-in system. Remember Nginx rewrite /students_system/ to /"
)

# --- 路由拆分 ---
router_admin = APIRouter(prefix="/api/admin", tags=["Admin"])
router_participant = APIRouter(prefix="/api/participant", tags=["Participant"])

# ==================================================
# 1. 管理员路由
# ==================================================

@router_admin.post("/login", response_model=models.Token)
async def login_for_access_token(form_data: models.AdminLogin):
    """
    管理员登录，获取 JWT Token
    """
    with get_db_connection() as db:
        admin = db_utils.get_admin_by_username(db, form_data.username)
    
    if not admin or not security.verify_password(form_data.password, admin['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={"sub": admin['username']}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router_admin.post("/activities", response_model=models.ActivityResponse)
async def create_activity(
    activity: models.ActivityCreate, 
    admin_user: str = Depends(security.get_current_admin)
):
    """
    创建新活动 (受保护)
    """
    with get_db_connection() as db:
        try:
            unique_code = db_utils.db_create_activity(db, activity)
            new_activity = db_utils.get_activity_by_code(db, unique_code)
            return new_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create activity: {e}")

@router_admin.get("/activities")
async def get_activities_list(admin_user: str = Depends(security.get_current_admin)):
    """
    获取所有活动列表 (受保护)
    """
    with get_db_connection() as db:
        activities = db_utils.get_all_activities(db)
        return activities

# 剪切这个函数 (原来在 router_admin 下)
@router_admin.get("/activities/{activity_code}/qr")
async def get_activity_qr_code(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    为活动生成签到二维码 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

    # 注意：URL 必须是 Nginx 暴露给外界的 URL
    checkin_url = f"https://havenchannel.xyz/students_system/checkin.html?code={activity_code}"

    img = qrcode.make(checkin_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@router_admin.get("/activities/{activity_code}/logs")
async def get_activity_logs(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    查看指定活动的签到/签退日志 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        logs = db_utils.get_check_logs_for_activity(db, activity['id'])
        return {"activity_name": activity['name'], "logs": logs}

@router_admin.delete("/activities/{activity_code}")
async def delete_activity(
    activity_code: str,
    admin_user: str = Depends(security.get_current_admin)
):
    """
    删除一个活动 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        try:
            db_utils.db_delete_activity(db, activity['id'])
            return {"message": "活动及所有签到记录已删除"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除失败: {e}")

@router_admin.put("/activities/{activity_code}")
async def update_activity_time(
    activity_code: str,
    time_update: models.ActivityTimeUpdate, # 使用我们新加的 model
    admin_user: str = Depends(security.get_current_admin)
):
    """
    更新活动时间 (受保护)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        try:
            db_utils.db_update_activity_time(
                db, activity['id'], time_update.start_time, time_update.end_time
            )
            # 返回更新后的活动信息
            updated_activity = db_utils.get_activity_by_code(db, activity_code)
            return updated_activity
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"更新失败: {e}")

# ==================================================
# 2. 参与者路由
# ==================================================

@router_participant.get("/activity/{activity_code}")
async def get_activity_details(activity_code: str):
    """
    获取单个活动的公开信息 (用于签到页面显示)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
    
    return {
        "name": activity['name'],
        "location_name": activity['location_name'],
        "start_time": activity['start_time'],
        "end_time": activity['end_time'],
        "latitude": activity['latitude'],      
        "longitude": activity['longitude'],    
        "radius_meters": activity['radius_meters'] 
    }

@router_participant.get("/activity/{activity_code}/qr") 
async def get_activity_qr_code(
    activity_code: str 
):
    """
    为活动生成签到二维码 (公开)
    """
    with get_db_connection() as db:
        activity = db_utils.get_activity_by_code(db, activity_code)
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

    checkin_url = f"https://havenchannel.xyz/students_system/checkin.html?code={activity_code}"
    
    img = qrcode.make(checkin_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")

@router_participant.post("/checkin", response_model=models.CheckInResponse)
async def participant_checkin(request: models.CheckInRequest):
    """
    参与者签到
    """
    try:
        now = datetime.now()
        with get_db_connection() as db:
            activity = db_utils.get_activity_by_code(db, request.activity_code)
            # 1. 校验活动是否存在
            if not activity:
                return JSONResponse(status_code=200, content={"detail": "活动不存在"})

            # 2. 校验时间
            if not (activity['start_time'] <= now <= activity['end_time']):
                return JSONResponse(status_code=200, content={"detail": "不在活动时间范围内"})

            # 3. 校验地点 (*** 修复 Decimal 报错 ***) ---   

            # 3a. 将活动坐标 (GCJ-02) 转回 WGS-84
            try:
                # 强制转换为 float，防止数据库返回 Decimal 类型导致 math 库报错
                act_lon_float = float(activity['longitude'])
                act_lat_float = float(activity['latitude'])
                
                act_wgs_lon, act_wgs_lat = coord_utils.gcj2wgs(act_lon_float, act_lat_float)
            except Exception as e:
                # 打印错误日志以便调试
                print(f"坐标转换错误: {e}") 
                raise HTTPException(status_code=500, detail=f"坐标转换失败 (活动): {str(e)}")

            # 3b. 将学生坐标 (GCJ-02) 转回 WGS-84
            try:
                # 前端传来的已经是 float，但为了保险也可以转一下
                req_lon_float = float(request.longitude)
                req_lat_float = float(request.latitude)
                
                req_wgs_lon, req_wgs_lat = coord_utils.gcj2wgs(req_lon_float, req_lat_float)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"坐标转换失败 (学生): {str(e)}")
            # 3c. 使用 WGS-84 坐标进行 haversine 计算
            try:
                distance = db_utils.calculate_distance(
                    act_wgs_lat, act_wgs_lon,
                    req_wgs_lat, req_wgs_lon
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"距离计算失败: {str(e)}")
                
            # [修改核心] 距离过远，返回 200 + 错误详情
            if distance > activity['radius_meters']:
                return JSONResponse(status_code=200, content={"detail": f"您不在签到范围内 (距离 {int(distance)} 米)"})
            # --- 修复结束 ---

            # 4. 获取或创建参与者
            participant = db_utils.get_participant(db, request.student_id)
            if not participant:
                participant = db_utils.create_participant(db, request.student_id, request.name)
                if not participant:
                     raise HTTPException(status_code=400, detail="学号已存在但姓名不匹配 (或创建用户失败)")
            elif participant['name'] != request.name:
                raise HTTPException(status_code=400, detail="学号与姓名不匹配")

            # 5. 检查是否已签到
            if db_utils.get_check_log(db, participant['id'], activity['id']):
                raise HTTPException(status_code=400, detail="您已签到，请勿重复操作")

            # 6. 创建签到记录
            try:
                device_token = db_utils.create_check_log(
                    db, activity['id'], participant['id'], request.latitude, request.longitude
                )
                return {"message": "签到成功", "device_session_token": device_token}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"签到失败: {e}")
    except HTTPException:
        # 重新抛出已知的HTTP异常
        raise
    except Exception as e:
        # 捕获所有其他异常并返回500错误
        raise HTTPException(status_code=500, detail=f"签到过程中发生未知错误: {str(e)}")

@router_participant.post("/checkout")
async def participant_checkout(request: models.CheckOutRequest):
    """
    参与者签退
    """
    try:
        now = datetime.now()
        with get_db_connection() as db:
            # 1. 验证 device_token 并获取签到记录
            log = db_utils.get_log_by_device_token(db, request.device_session_token)
            
            if not log:
                raise HTTPException(status_code=404, detail="无效的签到凭证，请使用签到设备重试")

            # 2. 检查是否已签退
            if log['check_out_time']:
                raise HTTPException(status_code=400, detail="您已签退，请勿重复操作")

            # 3. 校验时间 (使用联表查询出的活动时间)
            if not (log['start_time'] <= now <= log['end_time']):
                raise HTTPException(status_code=400, detail="不在活动时间范围内")

            # 4. 校验地点 (*** 修复 Decimal 报错 ***) ---

            # 4a. 将活动坐标 (GCJ-02) 转回 WGS-84
            try:
                # 强制转换为 float
                act_lon_float = float(log['longitude'])
                act_lat_float = float(log['latitude'])
                
                act_wgs_lon, act_wgs_lat = coord_utils.gcj2wgs(act_lon_float, act_lat_float)
            except Exception as e:
                print(f"坐标转换错误: {e}")
                raise HTTPException(status_code=500, detail=f"坐标转换失败 (活动): {str(e)}")

            # 4b. 将学生坐标 (GCJ-02) 转回 WGS-84
            try:
                req_lon_float = float(request.longitude)
                req_lat_float = float(request.latitude)
                
                req_wgs_lon, req_wgs_lat = coord_utils.gcj2wgs(req_lon_float, req_lat_float)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"坐标转换失败 (学生): {str(e)}")
            # 4c. 使用 WGS-84 坐标进行 haversine 计算
            try:
                distance = db_utils.calculate_distance(
                    act_wgs_lat, act_wgs_lon,
                    req_wgs_lat, req_wgs_lon
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"距离计算失败: {str(e)}")
                
            if distance > log['radius_meters']:
                return JSONResponse(status_code=200, content={"detail": f"您不在签退范围内 (距离 {int(distance)} 米)"})

            # 5. 更新签退记录
            try:
                db_utils.update_check_log_checkout(db, log['id'], request.latitude, request.longitude)
                return {"message": "签退成功"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"签退失败: {e}")
    except HTTPException:
        # 重新抛出已知的HTTP异常
        raise
    except Exception as e:
        # 捕获所有其他异常并返回500错误
        raise HTTPException(status_code=500, detail=f"签退过程中发生未知错误: {str(e)}")

# ==================================================
# 3. 注册路由和静态文件
# ==================================================
app.include_router(router_admin)
app.include_router(router_participant)

# 挂载静态文件 (前端页面)
# Nginx 会将 /students_system/ 转发到 /
# 所以 FastAPI 应该从 / 提供静态文件
import os
# 使用相对于app目录的静态文件路径
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")