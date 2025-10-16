# 以管理员身份运行此批处理文件
@echo off
echo Opening firewall for Flask application...

netsh advfirewall firewall add rule name="Flask App TCP 5000" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="Flask App TCP 5000 Out" dir=out action=allow protocol=TCP localport=5000

echo Firewall rules added successfully.
echo Checking rules...
netsh advfirewall firewall show rule name="Flask App TCP 5000"
pause