__coding__ = "utf-8"


def getClientIp(request):
    client_ip = ''
    if 'X-Forwarded-For' in request.headers:
        x_forwarded_for = request.headers['X-Forwarded-For']
        # 分割并获取最后一个IP地址
        client_ips = x_forwarded_for.split(',')
        client_ip = client_ips[-1].strip()
    else:
        # 如果没有 X-Forwarded-For 头部，则直接使用远程地址
        client_ip = request.remote_addr
    client_ip = client_ip.replace('.', '')
    return client_ip
