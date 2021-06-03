import sys
import sqlite3
import requests
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QFormLayout,QDialog,QComboBox,QTextEdit,QMenu,QAction,QDialogButtonBox,QLineEdit,QMessageBox
from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QMouseEvent, QIcon,QCursor
from settingDialog import dialog


'''
传入时间问题，不要每秒传一次时间
开始读取db里数据，依次检查，都有才开启timer
开始select找数据，判断，找不到数据，弹窗：请设置
找到数据，直接开始监控
'''



class mainWindow(QWidget):
    _startPos = None
    _endPos = None
    _isTracking = False

    def __init__(self, parent=None):
        super(mainWindow, self).__init__(parent)
        self.setFixedSize(100, 60)
        self.setWindowFlag(Qt.FramelessWindowHint)  # 无边框
        self.setWindowFlag(Qt.WindowStaysOnTopHint)  # 窗口置顶
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景透明
        # self.setWindowOpacity(0.9)
        self.setWindowIcon(QIcon("bitcoin.png"))  # 设置窗口图标
        self.form = QFormLayout()
        self.setLayout(self.form)
        self.labeldirection = QLabel()
        self.labeldirection.setStyleSheet('''
        QLabel {
            color:white;
        }
        ''')
        self.labelprice = QLabel('右键设置')
        self.labelprice.setStyleSheet('''
                QLabel {
                    color:white;
                }
                ''')
        self.labeldirection2 = QLabel()
        self.labeldirection2.setStyleSheet('''
                QLabel {
                    color:white;
                }
                ''')
        self.labelprice2 = QLabel('右键设置')
        self.labelprice2.setStyleSheet('''
                QLabel {
                    color:white;
                }
                ''')
        self.waitTime = 1000      #等待时间
        self.remainTime = 1000  #剩余时间
        self.form.addRow(self.labeldirection, self.labelprice)
        self.form.addRow(self.labeldirection2, self.labelprice2)
        self.time = QTimer()


        # 右键菜单
        # 将ContextMenuPolicy设置为Qt.CustomContextMenu,否则无法使用customContextMenuRequested信号
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # 创建QMenu信号事件
        self.customContextMenuRequested.connect(self.showMenu)
        self.contextMenu = QMenu(self)
        self.settingAction = self.contextMenu.addAction('设置')
        self.closeAction = self.contextMenu.addAction('关闭窗口')
        self.settingAction.triggered.connect(self.showSettingDialog)
        self.closeAction.triggered.connect(self.close)
        self.settingDialog = dialog()
        # 从数据库获取数据
        self.getData()

    # 双击关闭窗口
    def mouseDoubleClickEvent(self, e):
        self.time.stop()
        self.close()

    # 无边框拖动窗口
    def mouseMoveEvent(self, e: QMouseEvent):  # 重写移动事件
        self._endPos = e.pos() - self._startPos
        self.move(self.pos() + self._endPos)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = True
            self._startPos = QPoint(e.x(), e.y())

    def mouseReleaseEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self._isTracking = False
            self._startPos = None
            self._endPos = None

    def getData(self):
        # coin=highPrice=lowPrice=enterpriseId=agentId=secret = ''
        conn = sqlite3.connect('huobi.db')
        cur = conn.cursor()
        sql1 = '''
            CREATE TABLE IF NOT EXISTS huobi (id int primary key not null,
                                coin char(50) not null,
                                highPrice char(50) not null,
                                lowPrice char(50) not null,
                                timee int not null,
                                enterpriseId char(50) not null,
                                agentId char(50) not null,
                                secret char(50) not null);
        '''

        sql3 = '''
            select * from huobi
        '''
        sql4 = '''
            select count(*) as aaa from huobi
        '''
        cur.execute(sql1)
        # cur.execute(sql2)
        cur.execute(sql3)
        if len(list(cur)) != 1:
            QMessageBox.information(self, '提醒', '未设置参数，请右键进行设置', QMessageBox.Ok)
        else:
            cur.execute(sql3)
            for row in cur:
                coin = row[1]
                highPrice = row[2]
                lowPrice = row[3]
                timee = row[4]
                enterId = row[5]
                agentId = row[6]
                secret = row[7]
                print(coin,highPrice,lowPrice,timee,enterId,agentId,secret)
                self.waitTime = self.remainTime = timee
                self.time.timeout.connect(lambda coin=coin,
                                                 highPrice=highPrice,
                                                 lowPrice=lowPrice,
                                                 enterId=enterId,
                                                 appId=agentId,
                                                 secret=secret: self.getDataUi(coin, highPrice, lowPrice, enterId,
                                                                                    appId, secret))
                self.time.start(1000)
        # conn.commit()
        cur.close()
        conn.close()

        # return coin, highPrice, lowPrice, enterpriseId, agentId, secret

    # 获取动态币价
    def getDataUi(self,coin,highPrice,lowPrice,enterId,appId,secret):
        url = "https://api.hadax.com/market/history/trade?symbol={}&size=2".format(coin)

        try:
            r = requests.get(url)
        except:
            print("数据请求失败")

        datas = r.json()  # 将字符串序列转换为json
        datas = datas["data"]  # 获取数据列表

        self.price1 = datas[0]["data"][0]["price"]
        self.price2 = datas[1]["data"][0]["price"]
        self.bs1 = datas[0]["data"][0]["direction"]
        self.bs2 = datas[1]["data"][0]["direction"]
        # 实时更新价格在标签上
        self.labeldirection.setText(str(self.bs1)[0: 1] + ':')
        self.labelprice.setText(str(self.price1))
        self.labeldirection2.setText(str(self.bs2)[0: 1] + ':')
        self.labelprice2.setText(str(self.price2))
        # 高了发送消息
        if self.price1 > float(highPrice) and self.remainTime >= self.waitTime:
            self.remainTime -= 1
            self.sendWechatMessage(str(self.price1),enterId,appId,secret)
        # 低了发送消息
        if self.price1 < float(lowPrice) and self.remainTime >= self.waitTime:
            self.remainTime -= 1
            self.sendWechatMessage(str(self.price1),enterId,appId,secret)

        if self.remainTime < self.waitTime:
            self.remainTime -= 1
        if self.remainTime <= 0:
            self.remainTime = self.waitTime

    def sendWechatMessage(self,price,enterId,appId,secret):
        try:
            wx_push_access_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={}&corpsecret={}'.format(enterId,secret)
            wx_push_token = requests.post(wx_push_access_url, data="").json()['access_token']
            wx_push_data = {
                "agentid": appId,
                "msgtype": "text",
                "touser": "@all",
                "text": {
                    "content": "您监控的币种为DOGE\n" +
                               "目前价格为" + price + "\n" +
                               "快特么操作，不然分分钟变穷逼！"
                },
                "safe": 0
            }
            wx_push = requests.post('https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'.format(wx_push_token),
                          json=wx_push_data)
            print(wx_push.json())
            if wx_push.json()["errmsg"] == 'ok':

                self.settingDialog.close()


            else:
                self.time.stop()

                self.settingDialog.close()
                print('发送失败:agentId错误')
                QMessageBox.information(self, '提醒', '"AgentId"错误', QMessageBox.Ok)

        except:
            self.time.stop()

            self.settingDialog.close()
            print('enterID | secret ')
            QMessageBox.information(self, '提醒', '"企业ID"或"Secret"错误', QMessageBox.Ok)

    # 右键菜单槽
    def showMenu(self, pos):
        # pos 鼠标位置
        print(pos)
        # 菜单显示前,将它移动到鼠标点击的位置
        self.contextMenu.exec_(QCursor.pos())  # 在鼠标位置显示

    def showSettingDialog(self):

        self.settingDialog.buttons.accepted.connect(self.acceptSetting)
        self.settingDialog.exec_()

    def acceptSetting(self):
        print('确认设置')
        self.coin = self.settingDialog.comboCoin.currentText()
        self.high = self.settingDialog.textHigh.text().strip()
        self.low = self.settingDialog.textLow.text().strip()
        self.timee = self.settingDialog.textTime.text().strip()
        self.enterId = self.settingDialog.textEnterpriseId.text().strip()
        self.appId = self.settingDialog.textAppId.text().strip()
        self.secret = self.settingDialog.textSecret.text().strip()
        if self.high == '':
            QMessageBox.information(self,'提醒','请输入监控最高价',QMessageBox.Ok)
        elif self.low == '':
            QMessageBox.information(self,'提醒','请输入监控最低价',QMessageBox.Ok)
        elif self.low >= self.high:
            QMessageBox.information(self,'提醒','低价必须小于输入的高价',QMessageBox.Ok)
        elif self.timee == '':
            QMessageBox.information(self,'提醒','请输入提醒时间间隔(秒)',QMessageBox.Ok)
        elif self.enterId == '':
            QMessageBox.information(self,'提醒','请输入企业微信"企业ID"',QMessageBox.Ok)
        elif self.appId == '':
            QMessageBox.information(self,'提醒','请输入企业微信应用"AgentId"',QMessageBox.Ok)
        elif self.secret == '':
            QMessageBox.information(self,'提醒','请输入企业微信应用"Secret"码',QMessageBox.Ok)
        else:
            # 将数据写入数据库
            conn = sqlite3.connect('huobi.db')
            cur = conn.cursor()
            sql2 = '''
                                                    REPLACE INTO huobi (id,coin,highPrice,lowPrice,timee,enterpriseId,agentId,secret) values (1,?,?,?,?,?,?,?);
                                                '''
            cur.execute(sql2, (self.coin, self.high, self.low, self.timee, self.enterId, self.appId, self.secret))
            conn.commit()
            cur.close()
            conn.close()
            self.remainTime= self.waitTime=int(self.timee)
            self.time.timeout.connect(lambda coin = self.coin,
                                             highPrice = self.high,
                                             lowPrice = self.low,
                                             enterId = self.enterId,
                                             appId = self.appId,
                                             secret = self.secret :self.getDataUi(coin,highPrice,lowPrice,enterId,appId,secret))

            self.time.start(1000)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = mainWindow()
    window.show()
    sys.exit(app.exec_())