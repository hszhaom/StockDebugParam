


from app.services.google_sheet_client import GoogleSheet



# https://docs.google.com/spreadsheets/d/1Sp5pVox-hlo8Uz9Y3gqO154h07YeTkXQb0u0PtXQhDA/edit?gid=1967249531#gid=1967249531
gs = GoogleSheet(spreadsheet_id="1Sp5pVox-hlo8Uz9Y3gqO154h07YeTkXQb0u0PtXQhDA",sheet_name='data3y', token_file=r"C:\Users\Administrator\Desktop\谷歌参数批量校验\data\token.json")



a = gs.get_row(1)

print(a)