# 猜虚拟主播

一个适用于HoshinoBot的猜虚拟主播头像插件

## 如何安装

1. 在HoshinoBot的插件目录modules下clone本项目

   `git clone https://github.com/Rinco304/GuessVTB`

2. 在 `config/__bot__.py`的模块列表里加入 `GuessVTB`

3. 重启HoshinoBot

## 怎么使用

```
[猜vtb]	开始游戏
[猜vtb排行榜]	查看本群此游戏排行榜
[添加v别名 uid 别名1,别名2,...]  为此虚拟主播添加别名，可批量添加(使用 , 分隔)
例：添加v别名 327711614 本子助手,米露可
[查v别名 uid]	查询此vtb当前拥有的别名
[删除v别名 uid 别名1,别名2,...]  删除此虚拟主播的别名(仅维护组使用)
[更新vtb列表]	同步数据网站的vtb列表(仅维护组使用)
[更新v粉丝限制 数字]	设置少于多少粉丝的v不参与随机选择(仅维护组使用)
注：因为数据网站并没有记录vtb的别名，需要用户手动添加
在添加别名后下次再猜到此up时可以通过发送别名来回答，此时可以回答成功
没有别名的up只能回答官方名字才能回答成功
```

## 备注

此插件魔改自 [hoshinobot-plugin-ddcheck](https://github.com/benx1n/hoshinobot-plugin-ddcheck) 与Hoshino本体的pcr猜头像功能，代码质量不是很好，能用就行（

 VTB列表数据来源：[vtbs.moe](https://vtbs.moe/) 

建议首次使用时先使用 `更新vtb列表` 同步数据源信息

这个插件其实在4月份就改好了，当时因为数据源和自己并没有v的别名信息（现在也没有，只能自己添加）想着先在群里用着收集一下别名，等差不多了就发出来，结果时间一久忘了还有这事了😭

代码还可以优化（比如开始游戏和结束游戏都是发出get请求去获取头像、控制粉丝数限制方式是共享变量），但我太菜了再加上时间太久我也忘了改了些啥。总之功能是实现了的，如果有感兴趣的大佬可以帮忙研究研究！

关注兽耳助手喵，关注兽耳助手谢谢喵🥰

## 参考致谢

| [hoshinobot-plugin-ddcheck](https://github.com/benx1n/hoshinobot-plugin-ddcheck) | [@benx1n](https://github.com/benx1n/hoshinobot-plugin-ddcheck/commits?author=benx1n) |

| [avatar_guess](https://github.com/Ice9Coffee/HoshinoBot/blob/master/hoshino/modules/priconne/games/avatar_guess.py) | [@Ice9Coffee](https://github.com/Ice9Coffee) |
