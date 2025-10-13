import os.path
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread

# 如果您修改了此处的 SCOPES，那么需要删除旧的 token.json 文件，重新进行授权
# SCOPES 定义了您的应用程序需要访问 Google 服务的权限范围。
# 这里我们请求访问 Google Sheets 的读写权限。
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def generate_token_file():
    """
    通过 OAuth 2.0 授权流程生成并保存 token.json 文件。
    如果 token.json 文件已存在且有效，则直接加载。
    否则，将引导用户进行授权。
    """
    creds = None
    # token.json 存储了用户的访问和刷新令牌。
    # 它们在第一次授权成功后自动创建。
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # 如果没有有效的（或过期的）凭据，则让用户登录
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("令牌已过期，尝试刷新...")
            creds.refresh(Request())
        else:
            print("尚未获取或令牌无效，启动授权流程...")
            # `credentials.json` 是您从 Google Cloud Console 下载的客户端密钥文件
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            # 运行本地服务器，监听重定向 URI
            # 对于“桌面应用”类型，或者您在“已授权的重定向 URI”中设置了 http://localhost:端口号
            # 这将会自动在浏览器中打开授权页面
            creds = flow.run_local_server(port=5333) # port=0 会自动选择一个可用端口

        # 将凭据保存到 token.json 文件，以便下次运行时直接使用
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("token.json 文件已成功生成或更新。")
    else:
        print("token.json 文件已存在且凭据有效。")

    return creds

# --- 主程序部分 ---
if __name__ == '__main__':
    print("开始生成或加载 token.json 文件...")
    credentials = generate_token_file()

    if credentials:
        print("\n成功获取凭据！现在可以尝试使用 gspread 访问 Google Sheet。")
        try:
            # 使用获取到的凭据进行 gspread 认证
            # 注意：gspread.authorize 需要一个 `google.auth.credentials.Credentials` 对象
            # 而不是 gspread.service_account 
            gc = gspread.authorize(credentials)

            # 替换为您的 Google Sheet 名称
            spreadsheet_name = "Your Spreadsheet Name" # 例如 "My Expenses"
            # 您也可以使用 gc.open_by_key("your_spreadsheet_id")

            spreadsheet = gc.open(spreadsheet_name)
            worksheet = spreadsheet.sheet1
            print(f"成功连接到 Google Sheet: '{spreadsheet.title}'，工作表: '{worksheet.title}'")

            # 示例：读取数据
            # data = worksheet.get_all_values()
            # print("前5行数据：", data[:5])

        except gspread.exceptions.SpreadsheetNotFound:
            print(f"错误：未找到名为 '{spreadsheet_name}' 的 Google 表格。请确保名称正确，"
                  "且您用于授权的 Google 账号有权访问该表格。")
        except Exception as e:
            print(f"在访问 Google Sheet 时发生错误：{e}")
    else:
        print("未能获取有效的凭据。请检查您的配置。")
