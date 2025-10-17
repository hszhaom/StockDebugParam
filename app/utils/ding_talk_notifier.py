import requests
import time
import hmac
import hashlib
import base64
import urllib.parse


class DingTalkNotifier:
    """
    钉钉机器人通知类
    用于发送消息到钉钉群机器人
    {
        "msgtype": "text", // 消息类型，可为 text、link、markdown、actionCard、feedCard
        "text": {
            "content": "这是一条文本消息内容"
        },
        "link": {
            "messageUrl": "https://www.example.com", // 跳转链接
            "picUrl": "https://example.com/image.png", // 图片链接
            "text": "这是一条链接消息内容", // 消息内容
            "title": "链接消息标题" // 消息标题
        },
        "markdown": {
            "title": "Markdown消息标题",
            "text": "#### 这是Markdown消息内容 \n ![图片](https://example.com/image.png)"
        },
        "actionCard": {
            "title": "ActionCard消息标题",
            "text": "#### 这是ActionCard内容 \n ![图片](https://example.com/image.png)",
            "btnOrientation": "0", // 0-按钮竖直排列，1-按钮横向排列
            "singleTitle": "阅读全文", // 单个按钮标题
            "singleURL": "https://www.example.com", // 单个按钮跳转链接
            "btns": [
            {
                "title": "按钮1",
                "actionURL": "https://www.example.com/btn1"
            },
            {
                "title": "按钮2",
                "actionURL": "https://www.example.com/btn2"
            }
            ]
        },
        "feedCard": {
            "links": [
            {
                "title": "FeedCard标题1",
                "messageURL": "https://www.example.com/1",
                "picURL": "https://example.com/image1.png"
            },
            {
                "title": "FeedCard标题2",
                "messageURL": "https://www.example.com/2",
                "picURL": "https://example.com/image2.png"
            }
            ]
        },
        "at": {
            "isAtAll": false, // 是否@所有人
            "atUserIds": ["user001", "user002"], // 被@的用户ID列表
            "atMobiles": ["15xxx", "18xxx"] // 被@的手机号列表
        }
        }
        
    """

    def __init__(self, access_token, secret):
        """
        初始化钉钉通知器

        Args:
            access_token (str): 钉钉机器人的access_token
            secret (str): 钉钉机器人的签名密钥
        """
        self.access_token = access_token
        self.secret = secret
        self.base_url = 'https://oapi.dingtalk.com/robot/send'

    def _generate_signature(self):
        """
        生成签名用于安全验证

        Returns:
            tuple: (timestamp, sign) 时间戳和签名
        """
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def error_google_task_templates(self,task_id,error_msg,url):
        
        return {
            "msgtype": "actionCard", 
            "actionCard": {
                "title": "告警：当前任务报错",
                "text": f"#### 告警：当前任务报错 \n 报错id:{task_id} 报错异常：{error_msg}",
                "btnOrientation": "0", 
                "btns": [
                {
                    "title": "跳转报错任务",
                    "actionURL": url
                }
                ]
            },
            "at": {
                "isAtAll": False, # 是否@所有人
            }
            }


    def send_message(self,data):
        """
        发送消息到钉钉

        Args:
            :param data:
        Returns:
            dict: 响应结果
        """
        try:
            timestamp, sign = self._generate_signature()
            url = f'{self.base_url}?access_token={self.access_token}&timestamp={timestamp}&sign={sign}'
            response = requests.post(url, json=data)

            return response.json()
        except Exception as e:
            print(f"发送消息失败: {str(e)}")
            return {"error": str(e)}

# 使用示例
if __name__ == '__main__':
    # 初始化钉钉通知器
    notifier = DingTalkNotifier(
        access_token='a0fe95aac4a01a4c6826caf95087698baa6473804ee81dc2afaf4458e770eccc',
        secret='SEC3309a1318e963385c7a805d2530cb7d6f2128fe4c9f26673cbad7f599927a498'
    )


    # 发送消息
    result = notifier.send_message(notifier.error_templates())
    print(result)

