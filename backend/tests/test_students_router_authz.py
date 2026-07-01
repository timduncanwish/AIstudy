"""路由级测试：/students 的鉴权。

这是此前完全没被测过的一层——已有的 test_student_service.py 只测 service 函数，
不经过路由。

修复前：/students 全部接口只认客户端自报的 X-User-Id 头，不校验 JWT。谁只要
知道/猜到目标的 X-User-Id（登录时用 `wx_{openid[:16]}` 生成，参见
auth_service.py），不需要密码或 token 就能拿到该家长的完整读写权限，包括删除
孩子档案（LAUNCH_CHECKLIST.md 第10条）。

试过"有 token 就优先信 token"的折中方案，发现不够：攻击者只要干脆不带
Authorization 头、只带 X-User-Id，服务端仍会退回匿名回退逻辑并放行——这跟
应用里其它匿名接口的行为一致，不算真正修复。

最终方案（见 app/routers/students.py）：孩子档案含姓名/年级等儿童个人信息，
/students 全部接口改为强制要求已登录（有效 JWT），不再接受 X-User-Id 头兜底。
未登录请求一律 401。其它匿名可用接口（chat/homework/mistakes/preview/challenge）
不受影响，维持原样。
"""

from app.services.auth_service import wx_login


async def _login(db, code: str, nickname: str = "家长"):
    result = await wx_login(db, code=code, nickname=nickname)
    return result["token"]


async def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_unauthenticated_request_is_rejected(client):
    r = await client.get("/students")
    assert r.status_code == 401


async def test_x_user_id_header_alone_no_longer_grants_access(client):
    """核心回归：没有 token，只带 X-User-Id 头，不再能创建/访问孩子档案。"""
    r = await client.post(
        "/students", json={"name": "小明", "grade": 3}, headers={"X-User-Id": "wx_some_victim_id"}
    )
    assert r.status_code == 401


async def test_logged_in_user_can_manage_own_students(client, db):
    token = await _login(db, "aaaa_parent_a", "家长A")
    headers = await _auth_headers(token)

    create = await client.post("/students", json={"name": "小明", "grade": 3}, headers=headers)
    assert create.status_code == 200
    student_id = create.json()["id"]

    edit = await client.put(
        f"/students/{student_id}",
        json={"name": "小明明", "grade": None, "avatar_tag": None},
        headers=headers,
    )
    assert edit.status_code == 200
    assert edit.json()["name"] == "小明明"

    delete = await client.delete(f"/students/{student_id}", headers=headers)
    assert delete.status_code == 200

    verify = await client.get("/students", headers=headers)
    assert verify.json() == []


async def test_different_logged_in_users_are_isolated(client, db):
    # mock openid 只取 code 的前 4 位参与 device_id（wx_{openid[:16]}，
    # openid = "mock_openid_" 12 位 + code），前 4 位必须不同才不会撞同一账号
    token_a = await _login(db, "aaaa_parent_a", "家长A")
    token_b = await _login(db, "bbbb_parent_b", "家长B")

    create = await client.post(
        "/students", json={"name": "小红", "grade": 4}, headers=await _auth_headers(token_a)
    )
    student_id = create.json()["id"]

    edit = await client.put(
        f"/students/{student_id}",
        json={"name": "改名", "grade": None, "avatar_tag": None},
        headers=await _auth_headers(token_b),
    )
    assert edit.status_code == 404

    delete = await client.delete(f"/students/{student_id}", headers=await _auth_headers(token_b))
    assert delete.status_code == 404

    verify = await client.get("/students", headers=await _auth_headers(token_a))
    assert len(verify.json()) == 1
    assert verify.json()[0]["name"] == "小红"


async def test_knowing_victims_x_user_id_no_longer_enables_impersonation(client, db):
    """修复验证：即使攻击者知道受害者登录时会用到的 device_id 字符串，
    只带 X-User-Id、不带受害者的 token，也拿不到、改不了、删不掉数据。
    """
    code = "parent_e_code"
    token = await _login(db, code, "家长E")
    victim_device_id = f"wx_{f'mock_openid_{code}'[:16]}"

    create = await client.post(
        "/students", json={"name": "小刚", "grade": 5}, headers=await _auth_headers(token)
    )
    assert create.status_code == 200
    student_id = create.json()["id"]

    attacker_view = await client.get("/students", headers={"X-User-Id": victim_device_id})
    assert attacker_view.status_code == 401

    attacker_delete = await client.delete(
        f"/students/{student_id}", headers={"X-User-Id": victim_device_id}
    )
    assert attacker_delete.status_code == 401

    verify = await client.get("/students", headers=await _auth_headers(token))
    assert len(verify.json()) == 1
    assert verify.json()[0]["name"] == "小刚"


async def test_expired_or_garbage_token_is_rejected(client):
    r = await client.get("/students", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
