#  _*_ coding:utf-8
from flask import Flask, request, make_response
from xml.etree import cElementTree
import hashlib
import json
import time
import os
import sys
from wx_lib import sqllite
from os.path import dirname, join
from sys import argv
from wx_lib.wxconfig import DBfile


def sha1(data):
	m = hashlib.sha1()
	m.update(data.encode('utf-8'))
	return m.hexdigest()
app = Flask(__name__)


def check_mail(data):
	website_set = [
			'cn',
			'red',
			'com.cn',
			'wang',
			'cc',
			'xin',
			'ren',
			'com',
			'red',
			'pub',
			'co',
			'net',
			'org',
			'info',
			'xyz',
			'site',
			'club',
			'win'
	]
	split_data = data.strip().split('@')
	if len(split_data) != 2 or split_data[0] == "":
		return False
	web_site = split_data[1].split('.')
	if len(web_site) < 2 or web_site[1] not in website_set  or web_site[0] == "":
		return False
	return True


def get_token():
	path = join(dirname(argv[0]), "conf/token.json")
	with open(path, 'r') as f:
		data = f.read()
	return json.loads(data)


@app.route("/", methods=['GET', 'POST'])
def index():

	token = get_token()['token']
	if request.method == "GET":
		signature = request.args.get('signature')
		echostr = request.args.get('echostr')
		timestamp = request.args.get('timestamp')
		nonce = request.args.get('nonce')
		if not echostr and not signature and not timestamp and not nonce:
			return "参数错误"
		data = sorted([token, timestamp, nonce])
		return echostr.strip()
		#if sha1(''.join(data)) == signature.strip():
		#	return echostr.strip()
		#else:
		#	return "fail"
	else:
		msg = """<xml>
<ToUserName><![CDATA[%(openid)s]]></ToUserName>
<FromUserName><![CDATA[%(devid)s]]></FromUserName>
<CreateTime>%(time)s</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[%(content)s]]></Content>
</xml>"""

		xml_data = cElementTree.fromstring(request.stream.read())
		msgtype = xml_data.find("MsgType").text
		openid = xml_data.find("FromUserName").text
		fromusername = xml_data.find("ToUserName").text
		now_time = str(time.time())
		if msgtype.strip() == "event":
			if xml_data.find("Event").text.strip() == "subscribe":
				content = """欢迎关注运维微信,请直接回复邮箱地址绑定"""
				return make_response(msg % {'openid': openid, 'devid': fromusername, 'time': now_time, 'content': content})
			elif xml_data.find("Event").text.strip() == "unsubscribe":
				db_self = sqllite.Database()
				db_self.delete(wxid=openid)
				db_self.close()
				return "ok"
			else:
				return "fail"
		elif msgtype.strip() != "text":
			content = "仅支持文本消息,回复邮箱地址直接绑定"
			return make_response(msg % {'openid': openid, 'devid': fromusername, 'time': now_time, 'content': content})
		mail = xml_data.find("Content").text
		if check_mail(mail):
			DBfile.path = os.path.join(os.path.dirname(sys.argv[0]), 'conf/userinfo.db')
			db_self = sqllite.Database()
			mail_address = mail.strip()
			if not db_self.select(s_type='mail', data=mail_address) and not db_self.select(s_type='wxid', data=openid):
				if db_self.inster(openid, mail_address):
					content = "绑定成功,可以收取消息"
				else:
					content = "绑定失败"
			else:
				content = "您的微信已经绑定,无需在绑定"
			db_self.close()
		else:
			content = "请输入正确的邮箱格式"
		return make_response(msg % {'openid': openid, 'devid': fromusername, 'time': now_time, 'content': content})

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=80, debug=False)
