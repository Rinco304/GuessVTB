from nonebot import MessageSegment
from pathlib import Path
from PIL import Image

from hoshino import Service, util, aiorequests, priv
from hoshino.typing import CQEvent
from .util import get_vtb_list, get_facelink_by_uid, find_mid_by_name, get_vtb_list_by_mid, add_nickname_by_mid, update_vtb_list, delete_nickname_by_mid

import sqlite3, os, random, asyncio, io,re

sv_help = '''
[猜vtb] 开始游戏
[猜vtb排行榜] 查看本群此游戏排行榜
[添加v别名 uid 别名1,别名2,...] 为此虚拟主播添加别名，可批量添加(使用 , 分隔)
例：添加v别名 327711614 本子助手,米露可
[查v别名 uid] 查询此vtb当前拥有的别名
[删除v别名 uid 别名1,别名2,...] 删除此虚拟主播的别名(仅维护组使用)
[更新vtb列表] 同步数据网站的vtb列表(仅维护组使用)
[更新v粉丝限制 数字] 设置少于多少粉丝的v不参与随机选择(仅维护组使用)
注：因为数据网站并没有记录vtb的别名，需要用户手动添加
在添加别名后下次再猜到此up时可以通过发送别名来回答，此时可以回答成功
没有别名的up只能回答官方名字才能回答成功
'''.strip()

sv = Service(
    name = '猜vtb',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #可见性
    enable_on_default = True, #默认启用
    bundle = '娱乐', #分组归类
    help_ = sv_help #帮助说明
    )

PIC_SIDE_LENGTH = 25
# 一轮游戏持续时间
ONE_TURN_TIME = 20
# 粉丝数限制
FANS_LIMIT = 50000
DB_PATH = os.path.expanduser('~/.hoshino/pcr_vup_guess_winning_counter.db')

class WinnerJudger:
    def __init__(self):
        self.on = {}
        self.winner = {}
        self.correct_chara_id = {}
    
    def record_winner(self, gid, uid):
        self.winner[gid] = str(uid)
        
    def get_winner(self, gid):
        return self.winner[gid] if self.winner.get(gid) is not None else ''
        
    def get_on_off_status(self, gid):
        return self.on[gid] if self.on.get(gid) is not None else False
    
    def set_correct_chara_id(self, gid, cid):
        self.correct_chara_id[gid] = cid
    
    def get_correct_chara_id(self, gid):
        return self.correct_chara_id[gid] if self.correct_chara_id.get(gid) is not None else ''
    
    def turn_on(self, gid):
        self.on[gid] = True
        
    def turn_off(self, gid):
        self.on[gid] = False
        self.winner[gid] = ''
        self.correct_chara_id[gid] = ''


winner_judger = WinnerJudger()


class WinningCounter:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._create_table()


    def _connect(self):
        return sqlite3.connect(DB_PATH)


    def _create_table(self):
        try:
            self._connect().execute('''CREATE TABLE IF NOT EXISTS WINNINGCOUNTER
                          (GID             INT    NOT NULL,
                           UID             INT    NOT NULL,
                           COUNT           INT    NOT NULL,
                           PRIMARY KEY(GID, UID));''')
        except:
            raise Exception('创建表发生错误')
    
    
    def _record_winning(self, gid, uid):
        try:
            winning_number = self._get_winning_number(gid, uid)
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO WINNINGCOUNTER (GID,UID,COUNT) \
                                VALUES (?,?,?)", (gid, uid, winning_number+1))
            conn.commit()       
        except:
            raise Exception('更新表发生错误')


    def _get_winning_number(self, gid, uid):
        try:
            r = self._connect().execute("SELECT COUNT FROM WINNINGCOUNTER WHERE GID=? AND UID=?",(gid,uid)).fetchone()        
            return 0 if r is None else r[0]
        except:
            raise Exception('查找表发生错误')


async def get_user_card_dict(bot, group_id):
    mlist = await bot.get_group_member_list(group_id=group_id)
    d = {}
    for m in mlist:
        d[m['user_id']] = m['card'] if m['card']!='' else m['nickname']
    return d


def uid2card(uid, user_card_dict):
    return str(uid) if uid not in user_card_dict.keys() else user_card_dict[uid]


@sv.on_fullmatch(('猜VUP排行榜', '猜VUP群排行','猜vup排行榜', '猜vup群排行','猜VTB排行榜', '猜VTB群排行','猜vtb排行榜', '猜vtb群排行'))
async def description_guess_group_ranking(bot, ev: CQEvent):
    try:
        user_card_dict = await get_user_card_dict(bot, ev.group_id)
        card_winningcount_dict = {}
        winning_counter = WinningCounter()
        for uid in user_card_dict.keys():
            if uid != ev.self_id:
                card_winningcount_dict[user_card_dict[uid]] = winning_counter._get_winning_number(ev.group_id, uid)
        group_ranking = sorted(card_winningcount_dict.items(), key = lambda x:x[1], reverse = True)
        msg = '猜VUP小游戏此群排行为:\n'
        for i in range(min(len(group_ranking), 10)):
            if group_ranking[i][1] != 0:
                msg += f'第{i+1}名: {group_ranking[i][0]}, 猜对次数: {group_ranking[i][1]}次\n'
        await bot.send(ev, msg.strip())
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))


@sv.on_fullmatch(('猜vup','猜vtb','猜虚拟主播','猜VTB','猜VUP'))
async def up_guess(bot, ev: CQEvent):
    try:
        if winner_judger.get_on_off_status(ev.group_id):
            await bot.send(ev, "此轮游戏还没结束，请勿重复使用指令")
            return
        winner_judger.turn_on(ev.group_id)
        # 读取 json 文件
        vtb_list = await get_vtb_list()
        selected_vtb = None
        while selected_vtb is None or selected_vtb.get("follower", 0) < FANS_LIMIT:
            selected_vtb = random.choice(vtb_list)
        # 获取名字
        winner_judger.set_correct_chara_id(ev.group_id, selected_vtb["mid"])
        # 准备头像
        content = await (await aiorequests.get(await get_facelink_by_uid(selected_vtb["mid"]))).content
        image = Image.open(io.BytesIO(content))
        # 切割图，这里不做处理直接发送原头像
        # left = math.floor(random.random()*(129-PIC_SIDE_LENGTH))
        # upper = math.floor(random.random()*(129-PIC_SIDE_LENGTH))
        # cropped = img.crop((left, upper, left+PIC_SIDE_LENGTH, upper+PIC_SIDE_LENGTH))
        # file_path = os.path.join(dir_path, 'cropped_avatar.png')
        # cropped.save(file_path)
        cropped = MessageSegment.image(util.pic2b64(image))
        # image = MessageSegment.image(f'file:///{os.path.abspath(file_path)}')
        msg = f'猜猜这个图片是哪位虚拟主播的头像?({ONE_TURN_TIME}s后公布答案){cropped}'
        await bot.send(ev, msg)
        await asyncio.sleep(ONE_TURN_TIME)
        if winner_judger.get_winner(ev.group_id) != '':
            winner_judger.turn_off(ev.group_id)
            return
        msg =  f'正确答案是: {selected_vtb["uname"]}{cropped}\nUID:{selected_vtb["mid"]}\n很遗憾，没有人答对~\n若答对别名了但未成功可以帮忙添加一下别名~'
        winner_judger.turn_off(ev.group_id)
        await bot.send(ev, msg)
    except Exception as e:
        winner_judger.turn_off(ev.group_id)
        await bot.send(ev, '错误:\n' + str(e))
        
        
@sv.on_message()
async def on_input_chara_name(bot, ev: CQEvent):
    try:
        if winner_judger.get_on_off_status(ev.group_id):
            s = ev.message.extract_plain_text()
            uid = await find_mid_by_name(s, winner_judger.get_correct_chara_id(ev.group_id))
            selected_vtb = await get_vtb_list_by_mid(uid)
            if uid == winner_judger.get_correct_chara_id(ev.group_id) and winner_judger.get_winner(ev.group_id) == '':
                winner_judger.record_winner(ev.group_id, ev.user_id)
                winning_counter = WinningCounter()
                winning_counter._record_winning(ev.group_id, ev.user_id)
                winning_count = winning_counter._get_winning_number(ev.group_id, ev.user_id)
                user_card_dict = await get_user_card_dict(bot, ev.group_id)
                user_card = uid2card(ev.user_id, user_card_dict)
                msg_part = f'{user_card}猜对了，真厉害！TA已经猜对{winning_count}次了~\n(此轮游戏将在时间到后自动结束，请耐心等待)若答对别名了但未成功可以帮忙添加一下别名~'
                # 因为两次消息在不同的函数中，这里再次发出请求获得头像（待优化）
                content = await (await aiorequests.get(await get_facelink_by_uid(winner_judger.get_correct_chara_id(ev.group_id)))).content
                image = Image.open(io.BytesIO(content))
                cropped = MessageSegment.image(util.pic2b64(image))
                msg =  f'正确答案是: {selected_vtb["uname"]}{cropped}\nUID:{selected_vtb["mid"]}\n{msg_part}'
                await bot.send(ev, msg)
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))


@sv.on_prefix(('添加v别名', '添加V别名', '添加vtb别名', '添加VTB别名', '添加虚拟主播别名', '添加vup别名', '添加VUP别名', '设置v别名', '设置V别名'))
@sv.on_suffix(('添加v别名', '添加V别名', '添加vtb别名', '添加VTB别名', '添加虚拟主播别名', '添加vup别名', '添加VUP别名', '设置v别名', '设置V别名'))
async def add_nickname(bot,ev:CQEvent):
    content = ev.message.extract_plain_text().strip()
    try:
        # 正则表达式匹配 uid 和 nickname
        match = re.match(r'(\d+)\s+(.+)', content)
        if match:
            uid = match.group(1)
            nickname = match.group(2)
        else:
            await bot.send(ev, "输入格式不正确，请检查输入的uid是否正确且uid与别名间使用的是空格分隔")
            return
        nicknames = re.split(r"[,，]", nickname) if nickname else []
        # 强制转换uid为int类型
        result = await add_nickname_by_mid(int(uid), nicknames)
    except Exception as e:
        await bot.send(ev, '出现异常' + str(e))
    else:
        await bot.send(ev,result)


@sv.on_prefix(('删除v别名', '删除V别名', '删除vtb别名', '删除VTB别名', '删除虚拟主播别名', '删除vup别名', '删除VUP别名'))
@sv.on_suffix(('删除v别名', '删除V别名', '删除vtb别名', '删除VTB别名', '删除虚拟主播别名', '删除vup别名', '删除VUP别名'))
async def add_nickname(bot,ev:CQEvent):
    content = ev.message.extract_plain_text().strip()
    try:
        if not priv.check_priv(ev, priv.SUPERUSER):
            await bot.send(ev,'此功能仅限维护组使用')
            return
        # 正则表达式匹配 uid 和 nickname
        match = re.match(r'(\d+)\s+(.+)', content)
        if match:
            uid = match.group(1)
            nickname = match.group(2)
        else:
            await bot.send(ev, "输入格式不正确，请检查输入的uid是否正确且uid与别名之间使用的是空格分隔")
            return
        nicknames = re.split(r"[,，]", nickname) if nickname else []
        # 强制转换uid为int类型
        result = await delete_nickname_by_mid(int(uid), nicknames)
    except Exception as e:
        await bot.send(ev, '出现异常' + str(e))
    else:
        await bot.send(ev,result)


@sv.on_fullmatch(('更新vtb列表', '更新VTB列表', '更新虚拟直播列表'))
async def update_list(bot,ev:CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev,'此功能仅限维护组使用')
        return
    try:
        result = await update_vtb_list()
        await bot.send(ev, result)
    except Exception as e:
        await bot.send(ev, '更新列表时出现异常：' + str(e))


@sv.on_prefix(('更新v粉丝限制', '更新V粉丝限制', '更新vtb粉丝限制', '更新VTB粉丝限制'))
async def update_fans_limit(bot,ev:CQEvent):
    global FANS_LIMIT
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev,'此功能仅限维护组使用')
        return
    try:
        number = ev.message.extract_plain_text().strip()
        if re.match(r'^\d+$', number):
            fans_limit = int(number)
            if 0<= fans_limit <= 200000:
                FANS_LIMIT = fans_limit
                await bot.send(ev, f"修改成功，当前粉丝数限制为{FANS_LIMIT}")
            else:
                await bot.send(ev, "修改失败，请输入0-20w的整数")
        else:
            await bot.send(ev, "修改失败，请输入0-20w的整数")
    except Exception as e:
        await bot.send(ev, '修改粉丝数时出现异常：' + str(e))


@sv.on_prefix(('查v别名', '查V别名', '查vtb别名', '查VTB别名', '查虚拟主播别名', '查vup别名', '查vup别名'))
async def find_nickname_by_uid(bot,ev:CQEvent):
    try:
        uid = ev.message.extract_plain_text().strip()
        match = re.match(r'^[0-9]*$', uid)
        if match:
            vtb_info = await get_vtb_list_by_mid(int(uid))
            if not vtb_info:
                await bot.send(ev, '查询vtb信息失败，请检查uid是否正确，或者你想查询的vtb并未被数据网站收录')
            else:
                msg = f"用户名:{vtb_info['uname']}\nUID:{vtb_info['mid']}\n拥有的别名:"
                nickname = '、'.join(vtb_info['nickname'])
                msg += nickname
                await bot.send(ev,msg)
        else:
            await bot.send(ev,'查询vtb信息失败,请检查输入的uid是否正确')
    except Exception as e:
        await bot.send(ev, '出现异常：' + str(e))
