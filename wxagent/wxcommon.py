
import enum

WXAGENT_SERVICE_NAME = 'io.qtc.roundtable'
WXAGENT_SEND_PATH = '/io/qtc/roundtable'
WXAGENT_IFACE_NAME = 'io.qtc.roundtable.iface'

WXAGENT_EVENT_BUS_PATH = '/io/qtc/roundtable/signals'
WXAGENT_EVENT_BUS_IFACE = 'io.qtc.roundtable.signals'


######
class WXMsgType(enum.IntEnum):
    MT_TEXT = 1
    MT_FACE = 2
    MT_SHOT = 3
    MT_VOICE = 34  # 语音消息
    MT_X37 = 37  # 朋友推荐消息
    MT_X40 = 40  # xx邀请了xx加入了
    MT_X42 = 42  # 名片消息
    MT_X47_CARTOON = 47  # 像是群内动画表情，好友之间的动画表情
    MT_X49_FILE_OR_ARTICLE = 49  # 像是服务号消息,像是群内分享，像xml格式  # 一种是传的文件，一种是链接
    MT_X51 = 51  # 像是好友之间的图片消息
    MT_X10000 = 10000  # 系统通知？
    MT_X10002 = 10002  # 用户撤回了一条消息


USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.155 Safari/537.36'
REFERER = 'https://wx2.qq.com/?lang=en_US'

