# -*- coding=utf-8 -*-
import json
import httpx
from pathlib import Path
from typing import List
from nonebot.log import logger

data_path = Path("hoshino/modules/guessvtb/data")
# data_path = Path("data")
vtb_list_path = data_path / "vtb_list.json"


async def update_vtb_list():
    msg = "更新vtb列表失败，请稍后重试"
    vtb_list = []
    urls = [
        "https://api.vtbs.moe/v1/info"
        # "https://api.tokyo.vtbs.moe/v1/info",
        # "https://vtbs.musedash.moe/v1/info",
    ]
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                resp = await client.get(url, timeout=20)
                result = resp.json()
                if not result:
                    continue
                for info in result:
                    if info.get("mid", None) and info.get("uname", None):
                        vtb_info = {"mid": int(info["mid"]), "uname": info["uname"], "follower":int(info["follower"]), "nickname": []}
                        vtb_list.append(vtb_info)
                break
            except httpx.TimeoutException:
                logger.warning(f"Get {url} timeout")
            except Exception as e:
                print(e)
                logger.warning(f"Error when getting {url}, ignore")
        # 遍历更新后的列表，更新字典中已有的项的nickname字段
        old_vtb_list = load_vtb_list()
        for i, vtb_info in enumerate(vtb_list):
            for old_vtb_nickname in old_vtb_list:
                if old_vtb_nickname["mid"] == vtb_info["mid"]:
                    vtb_list[i]["nickname"] = old_vtb_nickname.get("nickname", [])
                    break
    dump_vtb_list(vtb_list)
    msg = "更新vtb列表成功"
    return msg


def dump_vtb_list(vtb_list: List[dict]):
    data_path.mkdir(parents=True, exist_ok=True)
    json.dump(
        vtb_list,
        vtb_list_path.open("w", encoding="utf-8"),
        indent=4,
        separators=(",", ": "),
        ensure_ascii=False,
    )


def load_vtb_list() -> List[dict]:
    if vtb_list_path.exists():
        with vtb_list_path.open("r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.decoder.JSONDecodeError:
                logger.warning("vtb列表解析错误，将重新获取")
                vtb_list_path.unlink()
    return []


async def get_vtb_list() -> List[dict]:
    vtb_list = load_vtb_list()
    if not vtb_list:
        await update_vtb_list()
    return load_vtb_list()

async def get_vtb_list_by_mid(mid: int) -> List[dict]:
    vtb_list = load_vtb_list()
    for vtb_info in vtb_list:
            if mid == vtb_info['mid']:
                return vtb_info
    return None


async def get_facelink_by_uid(uid: int) -> dict:
    try:
        url = "https://account.bilibili.com/api/member/getCardByMid"
        params = {"mid": uid}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            result = resp.json()
            return result["card"]["face"]
    except (KeyError, IndexError, httpx.TimeoutException) as e:
        logger.warning(f"Error in get_user_info({uid}): {e}")
        return {}


async def find_mid_by_name(name, correct_uid):
    vtb_list = load_vtb_list()
    for vtb_info in vtb_list:
        if (name in vtb_info['nickname'] or name == vtb_info['uname']) and vtb_info["mid"] == correct_uid:
            return vtb_info['mid']
    return None

async def add_nickname_by_mid(mid, nicknames):
    vtb_list = load_vtb_list()
    try:
        for vtb_info in vtb_list:
            if mid == vtb_info['mid']:
                existing_nicknames = vtb_info['nickname']
                for nickname in nicknames:
                    if nickname not in existing_nicknames:
                        vtb_info['nickname'].append(nickname)
                dump_vtb_list(vtb_list)
                msg = "添加别名成功"
                return msg
        msg = "添加别名失败，请检查输入的uid是否正确"
        return msg
    except Exception as e:
        logger.warning(f"出现异常：{e}")


async def delete_nickname_by_mid(mid, nicknames):
    vtb_list = load_vtb_list()
    try:
        for vtb_info in vtb_list:
            if mid == vtb_info['mid']:
                existing_nicknames = vtb_info['nickname']
                for nickname in nicknames:
                    if nickname in existing_nicknames:
                        vtb_info['nickname'].remove(nickname)
                dump_vtb_list(vtb_list)
                msg = "删除别名成功"
                return msg
        msg = "删除别名失败，请检查输入的uid是否正确"
        return msg
    except Exception as e:
        logger.warning(f"出现异常：{e}")
